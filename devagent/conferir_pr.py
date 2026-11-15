"""Confere a disciplina do ciclo num PR, sem depender da memória do agente.

Roda no CI (job `disciplina` do ci.yml) e pode rodar antes de abrir o PR:
    python -m devagent.conferir_pr [--base REF]

Compara a árvore de trabalho com o ponto em que a branch saiu da base
(padrão: origin/<GITHUB_BASE_REF> ou origin/main). Sem a base disponível,
só as regras que olham a árvore inteira rodam.

Regras (mantenha em sincronia com devagent/CICLO.md, Passos 1 e 4):
    1. Nenhuma spec fica `in-progress`. O status existe enquanto o agente
       trabalha; o PR leva a spec como `done` (ou não a toca).
    2. Arquivo de teste (`test_*.py`, `*_test.py`) só dentro de uma pasta
       `tests/`. Script de exploração não é versionado.
    3. Spec que vira `done` traz, no mesmo PR, o CHANGELOG (citando o número
       da spec) e o arquivo de estado do sistema.
    4. Correções antes de specs: um PR que começa e fecha uma spec enquanto a
       seção Correções do backlog tem entrada pendente precisa resolver uma
       dessas entradas (removê-la). Entradas que citam `bloqueado` não contam.
       Fechar uma spec que já estava `in-progress` na base é continuidade e
       não entra nesta regra.
    5. PR sem alteração nenhuma não entra. O PR #171 ("Spec 027a") chegou
       vazio, passou no CI e foi mergeado como se tivesse entregue a spec.
       Vale em `pull_request` no CI ou com `--exigir-alteracao`; num push na
       main a base é o próprio HEAD e a regra não se aplica.
    6. PR só de registro não entra: se tudo o que muda são relatórios de
       execução ou diários de persona, a execução não entregou nada e o PR
       só ocupa a fila (o #326, do Sentinel, só trazia o diário). Exceção:
       o corpo do PR fecha issues (`Closes #N`), como no Passo 6. Vale onde
       a regra 5 vale (ADR 012).
    7. Spec que vira `done` com o campo `aceite:` traz os testes listados ali,
       e o CI os roda. Specs a partir de `aceite_obrigatorio_desde` (seção
       [disciplina] do devagent.toml) precisam do campo. A 074 foi fechada sem
       remover nenhuma das tabelas que prometia (ADR 018).
    8. Cada raia escreve só na sua faixa (ADR 021). A raia sai do prefixo do
       título do PR (`spec:`, `revisão:`, `verificação:`; o resto é
       desenvolvimento) e devagent/raias.py diz o que cada uma pode tocar.
       É o que deixa as raias correrem em paralelo sem conflito. Vale no CI,
       onde o título do PR existe. Na raia de desenvolvimento, as specs só
       podem ter a linha `status:` trocada para `done`: criar, dividir ou
       editar spec é das raias de especificação e de revisão (ADR 023). O
       título precisa bater com a raia que o corpo declara no marcador
       `<!-- devagent:raia:<nome> -->` (ADRs 024 e 032), sem consulta externa;
       PR `revisão:` só cria partes (NNNa) da spec que altera e traz as linhas
       de conferência; PR `verificação:` traz achado novo. PR de pessoa fica
       fora da regra (ADR 024).
    9. Relatório novo (`docs/runs/` ou `docs/verificacao/relatorios/`) se
       chama AAAA-MM-DD-HHMM.md com a hora UTC em que foi escrito: no máximo
       10 min depois e 2 h antes do commit que o cria. O agente lê "os três
       últimos relatórios" pela ordem dos nomes; em 15/11, relatórios com a
       hora de Brasília e um com a data do dia seguinte (15-2129, escrito em
       15/11 00:50 UTC) faziam as sessões lerem como recentes relatórios de
       horas antes.
   10. O backlog é uma fila com teto e a ideia que vira spec sai dela. Todo
       PR que altera o backlog deixa a seção *Fila* com no máximo
       `teto_fila` linhas. Spec nova de PR `spec:`, a partir de
       `origem_obrigatoria_desde` ([disciplina] do devagent.toml), declara
       `origem:`: `nova`, `issue #N` ou o nome do item da Fila de onde veio.
       Com nome, o item precisa estar na Fila da base e sair dela no mesmo
       PR; se ficar com o resto da visão, a linha cita a spec nova
       (`spec NNN`). Em 15/11 o backlog tinha 318 linhas, boa parte já
       entregue, porque nada tirava a ideia que virava spec.

Uma regra nunca é afrouxada no mesmo PR que corrige o que ela aponta
(README do núcleo, separação de poderes).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from pathlib import Path

from devagent.config import CONFIG
from devagent.raias import (
    DESENVOLVIMENTO,
    ESPECIFICACAO,
    PASTA_SPECS,
    PASTA_VERIFICACAO,
    REVISAO,
    VERIFICACAO,
    edicao_de_spec_proibida,
    fora_da_raia,
    pr_do_agente,
    raia_declarada,
    raia_do_titulo,
    spec_nova_fora_do_alvo,
)

PASTA_ACHADOS = PASTA_VERIFICACAO + "achados/"
# Linhas que o corpo de todo PR `revisão:` traz (ADR 024).
CONFERENCIA_DA_REVISAO = ("Tamanho:", "Já no código:")

PADRAO_DOCUMENTOS = {
    "specs": "docs/specs",
    "backlog": "docs/BACKLOG.md",
    "changelog": "CHANGELOG.md",
    "estado": "docs/STATE.md",
    "secao_correcoes": "Correções",
    "secao_fila": "Fila",
    "teto_fila": 25,
}
# Prefixos de caminho que só registram a execução (relatório, diário).
PADRAO_REGISTROS = ("docs/runs/", ".jules/", ".agents/")
FECHA_ISSUE = re.compile(r"\b(close[sd]?|fix(e[sd])?|resolve[sd]?)\s+#\d+", re.I)

STATUS = re.compile(r"^status:\s*([\w-]+)\s*$", re.MULTILINE)
ID = re.compile(r"^id:\s*0*(\d+)\s*$", re.MULTILINE)
TESTE = re.compile(r"(^test_.*|.*_test)\.py$")
ORIGEM = re.compile(r"^origem:\s*(.*?)\s*$", re.MULTILINE)
ORIGEM_LIVRE = re.compile(r"^(nova|issue\s*#?\d+)$", re.I)
ACEITE = re.compile(r"^aceite:\s*(.*?)\s*$", re.MULTILINE)
ORDEM = re.compile(r"0*(\d+)([a-z]*)")


def ordem_de(spec_id: str) -> tuple[int, str]:
    m = ORDEM.search(spec_id.lower())
    return (int(m.group(1)), m.group(2)) if m else (0, "")


@dataclass
class Resultado:
    falhas: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)

    def falha(self, texto: str) -> None:
        self.falhas.append(texto)


def documentos() -> dict[str, str]:
    return {**PADRAO_DOCUMENTOS, **CONFIG.get("disciplina", {})}


def registros() -> tuple[str, ...]:
    return tuple(CONFIG.get("disciplina", {}).get("registros", PADRAO_REGISTROS))


def _campo_do_pr(campo: str) -> str:
    caminho = os.environ.get("GITHUB_EVENT_PATH")
    if not caminho or not Path(caminho).is_file():
        return ""
    try:
        evento = json.loads(Path(caminho).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    return str((evento.get("pull_request") or {}).get(campo) or "")


def autor_do_pr() -> str:
    """Login de quem abriu o PR no CI; vazio fora dele."""
    caminho = os.environ.get("GITHUB_EVENT_PATH")
    if not caminho or not Path(caminho).is_file():
        return ""
    try:
        evento = json.loads(Path(caminho).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    return str(
        ((evento.get("pull_request") or {}).get("user") or {}).get("login") or ""
    )


def conferir_raia_declarada(res: Resultado, raia: str, corpo: str) -> None:
    """A raia do título precisa bater com a raia declarada no corpo (ADRs 024 e 032).

    O corpo declara a raia no marcador `<!-- devagent:raia:<nome> -->`; a
    conferência é local, sem consultar serviço externo. Corpo sem marcador não
    é reprovado aqui: as faixas de arquivo da raia do título valem do mesmo jeito.
    """
    declarada = raia_declarada(corpo)
    if declarada and declarada != raia:
        res.falha(
            f"O PR declara a raia `{declarada}` no corpo, mas o título o coloca na raia de `{raia}`. "
            "Use o prefixo da sua raia (ADRs 024 e 032)."
        )


def corpo_do_pr() -> str:
    """Corpo do PR no CI (evento pull_request); vazio fora dele."""
    return _campo_do_pr("body")


def titulo_do_pr() -> str:
    """Título do PR no CI (evento pull_request); vazio fora dele."""
    return _campo_do_pr("title")


def git(*args: str, raiz: Path) -> str | None:
    r = subprocess.run(
        ["git", *args], cwd=raiz, capture_output=True, text=True, check=False
    )
    return r.stdout if r.returncode == 0 else None


def status_de(texto: str | None) -> str | None:
    if texto is None:
        return None
    m = STATUS.search(texto)
    return m.group(1) if m else None


def id_de(texto: str, caminho: str) -> str:
    m = ID.search(texto)
    if m:
        return m.group(1)
    num = re.match(r"0*(\d+)", Path(caminho).name)
    return num.group(1) if num else Path(caminho).stem


def entradas_correcoes(texto: str | None, secao: str) -> list[str]:
    """Itens de primeiro nível da seção Correções, sem os que citam bloqueio."""
    if not texto:
        return []
    dentro = False
    itens: list[str] = []
    for linha in texto.splitlines():
        if linha.startswith("## "):
            dentro = linha[3:].strip().lower().startswith(secao.lower())
            continue
        if dentro and linha.startswith("- "):
            itens.append(linha.strip())
    return [i for i in itens if "bloqueado" not in i.lower()]


def _normalizar(texto: str) -> str:
    return re.sub(r"\s+", " ", texto.replace("`", "").replace("*", "")).strip().lower()


def itens_da_fila(texto: str | None, secao: str) -> list[tuple[str, str]]:
    """(nome normalizado, linha inteira) de cada item da tabela da seção Fila.

    O nome é a coluna "Ideia" da tabela; sem essa coluna, a terceira.
    """
    if not texto:
        return []
    dentro = False
    coluna: int | None = None
    itens: list[tuple[str, str]] = []
    for linha in texto.splitlines():
        if linha.startswith("## "):
            dentro = linha[3:].strip().lower().startswith(secao.lower())
            coluna = None
            continue
        if not dentro or not linha.startswith("|"):
            continue
        celulas = [c.strip() for c in linha.strip().strip("|").split("|")]
        if coluna is None:
            nomes = [_normalizar(c) for c in celulas]
            coluna = (
                nomes.index("ideia") if "ideia" in nomes else min(2, len(celulas) - 1)
            )
            continue
        if set("".join(celulas)) <= set("-: "):
            continue
        if coluna < len(celulas):
            itens.append((_normalizar(celulas[coluna]), linha))
    return itens


def conferir_fila(
    res: Resultado,
    antes: str | None,
    depois: str | None,
    specs_novas: list[tuple[str, str]],
    secao: str,
    teto: int,
) -> None:
    """Regra 10: teto da Fila e a ideia que vira spec sai dela.

    `specs_novas` traz (caminho, texto) das specs criadas pelo PR que precisam
    declarar `origem:`; `antes` e `depois` são o backlog na base e no PR (None
    quando o backlog não mudou e não precisa ser conferido).
    """
    fila_depois = itens_da_fila(depois, secao)
    if depois is not None and len(fila_depois) > teto:
        res.falha(
            f"A seção {secao} do backlog tem {len(fila_depois)} itens; o teto é "
            f"{teto}. Ideia nova desloca a última da fila para a Reserva "
            "(CICLO.md, Passo 7, item 4a)."
        )
    nomes_antes = {n for n, _ in itens_da_fila(antes, secao)}
    for rel, texto in specs_novas:
        m = ORIGEM.search(texto)
        origem = m.group(1).strip() if m else ""
        if not origem:
            res.falha(
                f"{rel} não declara `origem:` no cabeçalho: `nova`, `issue #N` ou "
                f"o nome do item da {secao} do backlog de onde a spec veio "
                "(regra 10)."
            )
            continue
        if ORIGEM_LIVRE.match(origem):
            continue
        nome = _normalizar(origem)
        if nome not in nomes_antes:
            res.falha(
                f"{rel}: a origem `{origem}` não é o nome de nenhum item da "
                f"{secao} do backlog na base. Copie o nome da coluna Ideia, ou use "
                "`nova` se a ideia nasceu nesta rodada (regra 10)."
            )
            continue
        numero = re.match(r"0*(\d+)", Path(rel).name)
        cita = re.compile(rf"spec\s+0*{numero.group(1) if numero else '-'}(?!\d)", re.I)
        restante = [linha for n, linha in fila_depois if n == nome]
        if restante and not any(cita.search(linha) for linha in restante):
            res.falha(
                f"{rel} veio do item `{origem}`, que continua na {secao} do "
                "backlog. Tire o item no mesmo PR ou, se ele guarda o resto da "
                f"visão, cite a spec nova na linha (regra 10)."
            )


PASTAS_DE_RELATORIO = ("docs/runs/", "docs/verificacao/relatorios/")
NOME_DE_RELATORIO = re.compile(r"(\d{4})-(\d{2})-(\d{2})-(\d{2})(\d{2})\.md$")
FOLGA_DEPOIS = timedelta(minutes=10)
FOLGA_ANTES = timedelta(hours=2)


def hora_do_relatorio_errada(rel: str, quando: datetime) -> str:
    """Por que o nome do relatório não é a hora UTC de `quando`; vazio se é.

    `quando` é a hora do commit que cria o relatório (ou agora, antes do
    commit). Nome fora do padrão AAAA-MM-DD-HHMM.md não entra na regra.
    """
    m = NOME_DE_RELATORIO.search(rel)
    if not m:
        return ""
    try:
        nome = datetime(*map(int, m.groups()), tzinfo=timezone.utc)
    except ValueError:
        return f"{rel}: o nome não é uma data e hora válidas."
    quando = quando.astimezone(timezone.utc)
    if quando - FOLGA_ANTES <= nome <= quando + FOLGA_DEPOIS:
        return ""
    certo = quando.strftime("%Y-%m-%d-%H%M")
    return (
        f"{rel}: o nome do relatório é a hora UTC em que ele foi escrito "
        f"(`date -u +%Y-%m-%d-%H%M`), por volta de {certo}. As sessões leem "
        "os três últimos relatórios pela ordem dos nomes (regra 9)."
    )


def arquivos_versionados(raiz: Path) -> list[str]:
    saida = git("ls-files", "--cached", "--others", "--exclude-standard", raiz=raiz)
    return [linha for linha in (saida or "").splitlines() if linha]


def resolver_base(raiz: Path, base: str | None) -> str | None:
    candidatos = [base] if base else []
    alvo = os.environ.get("GITHUB_BASE_REF")
    if alvo:
        candidatos.append(f"origin/{alvo}")
    candidatos.append("origin/main")
    for ref in candidatos:
        if ref and git("rev-parse", "--verify", "--quiet", ref, raiz=raiz):
            mb = git("merge-base", "HEAD", ref, raiz=raiz)
            if mb:
                return mb.strip()
    return None


def conferir(
    raiz: Path,
    base: str | None = None,
    exigir_alteracao: bool | None = None,
    titulo: str | None = None,
    corpo: str | None = None,
) -> Resultado:
    if exigir_alteracao is None:
        exigir_alteracao = os.environ.get("GITHUB_EVENT_NAME") == "pull_request"
    doc = documentos()
    res = Resultado()
    pasta_specs = raiz / doc["specs"]

    # Regra 1: nenhuma spec in-progress.
    specs_atuais: dict[str, str] = {}
    if pasta_specs.is_dir():
        for p in sorted(pasta_specs.glob("*.md")):
            rel = p.relative_to(raiz).as_posix()
            specs_atuais[rel] = p.read_text(encoding="utf-8")
    for rel, texto in specs_atuais.items():
        if status_de(texto) == "in-progress":
            res.falha(
                f"{rel} está `in-progress`. Termine a spec e marque `done` neste "
                "PR (com CHANGELOG e estado do sistema) ou devolva para `ready`."
            )

    # Regra 2: testes só dentro de tests/.
    for caminho in arquivos_versionados(raiz):
        partes = Path(caminho).parts
        if TESTE.match(partes[-1]) and "tests" not in partes[:-1]:
            res.falha(
                f"{caminho} parece teste ou script de exploração fora de `tests/`. "
                "Mova para `tests/` ou apague do PR."
            )

    mb = resolver_base(raiz, base)
    if mb is None:
        res.avisos.append(
            "base não encontrada (faça fetch de origin/main): regras 3 e 4 puladas."
        )
        return res

    # Arquivos tocados desde a base: commits da branch, mudanças ainda não
    # commitadas e arquivos novos ainda fora do índice.
    alterados = set((git("diff", "--name-only", mb, raiz=raiz) or "").split())
    novos = git("ls-files", "--others", "--exclude-standard", raiz=raiz) or ""
    alterados |= set(novos.split())

    # Regra 5: PR vazio.
    if exigir_alteracao and not alterados:
        res.falha(
            "O PR não altera nenhum arquivo em relação à base. Um PR vazio não "
            "entrega nada: faça commit do trabalho nesta branch ou feche o PR. "
            "Se a sessão perdeu as mudanças, devolva a spec para `ready` e "
            "registre o motivo no relatório."
        )

    # Regra 9: relatório novo com a hora UTC em que foi escrito.
    adicionados = set(
        (git("diff", "--name-only", "--diff-filter=A", mb, raiz=raiz) or "").split()
    ) | set(novos.split())
    for rel in sorted(adicionados):
        if not rel.startswith(PASTAS_DE_RELATORIO):
            continue
        commit = git(
            "log", "--diff-filter=A", "--format=%cI", "-1", "--", rel, raiz=raiz
        )
        quando = (
            datetime.fromisoformat(commit.strip())
            if commit and commit.strip()
            else datetime.now(timezone.utc)
        )
        motivo = hora_do_relatorio_errada(rel, quando)
        if motivo:
            res.falha(motivo)

    # Regra 6: PR só de registro.
    prefixos = registros()
    if (
        exigir_alteracao
        and alterados
        and all(a.startswith(prefixos) for a in alterados)
        and not FECHA_ISSUE.search(corpo_do_pr())
    ):
        res.falha(
            "O PR só altera registros da execução ("
            + ", ".join(sorted(alterados))
            + "). Execução sem entrega não abre PR: siga para o próximo passo do "
            "ciclo nesta mesma sessão e leve o registro no PR que ele produzir "
            "(CICLO.md, seção 4; especialistas.md, regra 7)."
        )

    # Regra 8: cada raia escreve só na sua faixa. PR de pessoa (o dono do
    # produto) não é de raia nenhuma e fica de fora (ADR 024). PR do agente é
    # o de login conhecido ou o que declara a raia no corpo: as sessões abrem
    # PR com o login do dono do repositório (raias.pr_do_agente).
    titulo = titulo_do_pr() if titulo is None else titulo
    corpo = corpo_do_pr() if corpo is None else corpo
    autor = autor_do_pr()
    if autor and not pr_do_agente(autor, corpo):
        titulo = ""
    if titulo and alterados:
        raia = raia_do_titulo(titulo)
        invasoes = fora_da_raia(raia, alterados)
        if invasoes:
            onde = (
                "pertencem a outra raia"
                if raia == DESENVOLVIMENTO
                else "estão fora do que a raia pode alterar"
            )
            res.falha(
                f"O título coloca este PR na raia de {raia}, e estes arquivos "
                f"{onde}: {', '.join(invasoes)}. Tire-os do PR ou corrija o "
                "prefixo do título (devagent/raias.py, ADR 021)."
            )
        if raia == DESENVOLVIMENTO:
            for rel in sorted(a for a in alterados if a.startswith(PASTA_SPECS)):
                if not rel.endswith(".md"):
                    continue
                caminho = raiz / rel
                depois = (
                    caminho.read_text(encoding="utf-8") if caminho.exists() else None
                )
                antes = git("show", f"{mb}:{rel}", raiz=raiz)
                motivo = edicao_de_spec_proibida(antes, depois)
                if motivo:
                    res.falha(
                        f"{rel}: {motivo}. O desenvolvimento não cria, não divide "
                        "e não edita specs; isso é das raias de especificação e "
                        "de revisão. O único toque permitido é mudar `status:` "
                        "para `done` ao entregar (ADR 023). Tire a spec do PR."
                    )
        conferir_raia_declarada(res, raia, corpo)
        specs_mudadas = sorted(
            a for a in alterados if a.startswith(PASTA_SPECS) and a.endswith(".md")
        )
        if raia == REVISAO:
            novas = [
                a for a in specs_mudadas if git("show", f"{mb}:{a}", raiz=raiz) is None
            ]
            existentes = [a for a in specs_mudadas if a not in novas]
            fora = spec_nova_fora_do_alvo(novas, existentes)
            if fora:
                res.falha(
                    "O Revisor só divide a spec que revisa, em partes com sufixo "
                    f"de letra (NNNa, NNNb). Estas specs novas não são partes de uma "
                    f"spec alterada no PR: {', '.join(fora)}. Número novo é do "
                    "Especificador (ADR 024)."
                )
            faltam = [r for r in CONFERENCIA_DA_REVISAO if r not in corpo]
            if exigir_alteracao and faltam:
                res.falha(
                    "O corpo do PR `revisão:` precisa das linhas "
                    + ", ".join(f"`{r}`" for r in faltam)
                    + ": quantos arquivos a spec toca (saída do `grep -rl`, "
                    "contando os testes) e se o código atual já faz o que ela "
                    "pede. Revisão que só ajusta a forma não pega spec grande "
                    "nem duplicada (ADR 024)."
                )
        if raia == VERIFICACAO and exigir_alteracao:
            achados = [
                a
                for a in alterados
                if a.startswith(PASTA_ACHADOS)
                and git("show", f"{mb}:{a}", raiz=raiz) is None
            ]
            if not achados:
                res.falha(
                    "PR de verificação sem achado novo em "
                    f"`{PASTA_ACHADOS}`. Sem achado, sem PR: encerre a sessão "
                    "sem commit (devagent/agents/raias.md, ADR 024)."
                )

    # Regra 10: a Fila do backlog tem teto e a ideia que vira spec sai dela.
    backlog_mudou = doc["backlog"] in alterados
    caminho_backlog = raiz / doc["backlog"]
    backlog_depois = (
        caminho_backlog.read_text(encoding="utf-8")
        if caminho_backlog.exists()
        else None
    )
    specs_com_origem: list[tuple[str, str]] = []
    desde_origem = str(CONFIG.get("disciplina", {}).get("origem_obrigatoria_desde", ""))
    if titulo and desde_origem and raia_do_titulo(titulo) == ESPECIFICACAO:
        for rel, texto in specs_atuais.items():
            if (
                rel not in alterados
                or git("show", f"{mb}:{rel}", raiz=raiz) is not None
            ):
                continue
            if ordem_de(Path(rel).name.split("-")[0]) >= ordem_de(desde_origem):
                specs_com_origem.append((rel, texto))
    if backlog_mudou or specs_com_origem:
        conferir_fila(
            res,
            git("show", f"{mb}:{doc['backlog']}", raiz=raiz),
            backlog_depois,
            specs_com_origem,
            doc["secao_fila"],
            int(doc["teto_fila"]),
        )

    fechadas_novas: list[str] = []
    fechadas: list[tuple[str, str]] = []
    for rel, texto in specs_atuais.items():
        if status_de(texto) != "done":
            continue
        antes = status_de(git("show", f"{mb}:{rel}", raiz=raiz))
        if antes == "done":
            continue
        numero = id_de(texto, rel)
        fechadas.append((rel, numero))
        if antes != "in-progress":
            fechadas_novas.append(rel)

    # Regra 3: spec fechada leva CHANGELOG (citando o número) e estado.
    if fechadas:
        adicionadas = "\n".join(
            linha[1:]
            for linha in (
                git("diff", "-U0", mb, "--", doc["changelog"], raiz=raiz) or ""
            ).splitlines()
            if linha.startswith("+") and not linha.startswith("+++")
        )
        for rel, numero in fechadas:
            if not re.search(rf"(?<!\d)0*{numero}(?!\d)", adicionadas):
                res.falha(
                    f"{rel} virou `done`, mas o {doc['changelog']} não ganhou uma "
                    f"linha citando a spec {numero}."
                )
        if doc["estado"] not in alterados:
            nomes = ", ".join(n for _, n in fechadas)
            res.falha(
                f"Spec(s) {nomes} viraram `done`, mas {doc['estado']} não foi "
                "atualizado (o que foi implementado e o contador de painéis)."
            )

    # Regra 4: Correções antes de specs novas.
    if fechadas_novas:
        pendentes = entradas_correcoes(
            git("show", f"{mb}:{doc['backlog']}", raiz=raiz), doc["secao_correcoes"]
        )
        caminho_backlog = raiz / doc["backlog"]
        atuais = set(
            entradas_correcoes(
                caminho_backlog.read_text(encoding="utf-8")
                if caminho_backlog.exists()
                else None,
                doc["secao_correcoes"],
            )
        )
        resolvidas = [e for e in pendentes if e not in atuais]
        if pendentes and not resolvidas:
            res.falha(
                f"Este PR fecha {', '.join(fechadas_novas)}, mas a seção "
                f"{doc['secao_correcoes']} de {doc['backlog']} tem entrada pendente: "
                f"{pendentes[0][:120]}... Correções vêm antes de specs (CICLO.md, "
                "Passo 1, item 6). Trate a primeira entrada e remova-a no mesmo PR."
            )

    # Regra 7: aceite executável. Olha também as subpastas (done/), para onde
    # algumas specs são movidas ao fechar.
    desde = str(CONFIG.get("disciplina", {}).get("aceite_obrigatorio_desde", ""))
    if pasta_specs.is_dir():
        for p in sorted(pasta_specs.rglob("*.md")):
            texto = p.read_text(encoding="utf-8")
            if status_de(texto) != "done":
                continue
            rel = p.relative_to(raiz).as_posix()
            antes = status_de(git("show", f"{mb}:{rel}", raiz=raiz))
            if antes is None:
                topo = f"{doc['specs']}/{p.name}"
                antes = status_de(git("show", f"{mb}:{topo}", raiz=raiz))
            if antes == "done":
                continue
            m = ACEITE.search(texto)
            listados = re.split(r"[,\s]+", m.group(1)) if m else []
            listados = [a for a in listados if a]
            numero = p.name.split("-")[0]
            if not listados:
                if desde and ordem_de(numero) >= ordem_de(desde):
                    res.falha(
                        f"{rel} virou `done` sem o campo `aceite:`. Specs a partir "
                        f"da {desde} listam ali o teste que prova a entrega."
                    )
                continue
            for arquivo in listados:
                if not (raiz / arquivo.split("::")[0]).is_file():
                    res.falha(
                        f"{rel} virou `done`, mas o teste de aceite `{arquivo}` não "
                        "existe. Escreva o teste (ele é a prova da entrega) ou "
                        "devolva a spec para `ready`."
                    )
    return res


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base", help="ref da base (padrão: origin/main)")
    ap.add_argument("--raiz", default=".", help="raiz do repositório")
    ap.add_argument(
        "--exigir-alteracao",
        action="store_true",
        default=None,
        help="reprova se não houver arquivo alterado (padrão: só em pull_request)",
    )
    args = ap.parse_args(argv)

    res = conferir(Path(args.raiz).resolve(), args.base, args.exigir_alteracao)
    for aviso in res.avisos:
        print(f"aviso: {aviso}")
    if res.falhas:
        print("Disciplina do ciclo: o PR não está pronto.\n")
        for f in res.falhas:
            print(f"- {f}")
        return 1
    print("Disciplina do ciclo: ok.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
