"""Qual papel esta sessão assume e qual é o alvo concreto dela (ADR 033).

Uma raia que para trava as outras: sem o Revisor, nenhuma spec chega ao
desenvolvimento; sem o Especificador, a fila seca. Enquanto havia um
orquestrador externo, era ele quem abria a sessão de cada raia com o alvo no
prompt. Quando ele saiu e ninguém ficou no lugar, a fila inteira esperou a
revisão e o desenvolvimento passou dez rodadas seguidas melhorando a si mesmo.

Aqui a decisão volta para o código, sem depender de quem agenda as sessões:

    python -m devagent.papel               # o papel desta sessão
    python -m devagent.papel revisor       # o alvo de uma persona nomeada
    python -m devagent.papel especificador
    python -m devagent.papel verificador
    python -m devagent.papel conferir revisor 150   # o alvo ainda está livre?

Sem argumento, a sessão é do desenvolvedor, salvo quando ele não tem trabalho
de produto e outra raia está parada: aí a sessão assume essa raia por inteiro
(a persona de `devagent/agents/raias.md`, não o ciclo). O `estado_github`
imprime a mesma decisão no primeiro comando.

As funções de decisão são puras; só o `main` consulta o GitHub e o git.
Só usa a biblioteca padrão.
"""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from devagent.fila_specs import (
    fila_da_revisao,
    fila_do_desenvolvimento,
    issue_prioritaria,
    producao_pendente,
    proximo_numero,
    spec_para_dividir,
    specs_prontas,
    tentativas_da_spec,
)
from devagent.raias import (
    DESENVOLVIMENTO,
    ESPECIFICACAO,
    PASTA_VERIFICACAO,
    REVISAO,
    VERIFICACAO,
    raia_do_titulo,
)

DESENVOLVEDOR = "desenvolvedor"
REVISOR = "revisor"
ESPECIFICADOR = "especificador"
VERIFICADOR = "verificador"

RAIA_DA_PERSONA = {
    REVISOR: REVISAO,
    ESPECIFICADOR: ESPECIFICACAO,
    VERIFICADOR: VERIFICACAO,
}
NOME = {
    DESENVOLVEDOR: "desenvolvedor",
    REVISOR: "Revisor",
    ESPECIFICADOR: "Especificador",
    VERIFICADOR: "Verificador",
}

# Com a fila de specs ready neste tamanho ou menor, o Especificador prepara a
# próxima (ADR 029).
FILA_PARA_ESPECIFICAR = 2
# Entregas seguidas da raia de desenvolvimento sem nenhuma spec, com spec ready
# na fila, a partir das quais a fila é tratada como travada.
LIMITE_SEM_SPEC = 4
# Sem relatório anterior (ou com um antigo), o Verificador olha só este período.
JANELA_DA_VERIFICACAO = timedelta(hours=24)

ENTREGA_DE_SPEC = re.compile(r"^(feat|refactor)\b", re.IGNORECASE)
RELATORIO = re.compile(r"(\d{4})-(\d{2})-(\d{2})-(\d{2})(\d{2})\.md$")


@dataclass(frozen=True)
class Papel:
    persona: str
    # Por que a sessão é desta persona.
    motivo: str
    # O trabalho concreto; vazio quando a persona não tem o que fazer.
    alvo: str = ""

    def frase(self) -> str:
        """O que o `estado_github` imprime no primeiro comando."""
        if self.persona == DESENVOLVEDOR:
            return " ".join(t for t in (self.motivo, self.alvo) if t)
        return (
            f"Esta sessão atua como {NOME[self.persona]}, não como desenvolvedor: "
            f"{self.motivo} Siga `devagent/agents/raias.md` e ignore o ciclo de "
            f"decisão. {self.alvo}"
        )


def _relativo(caminho: Path, raiz: Path | None = None) -> str:
    try:
        return caminho.relative_to(raiz or Path.cwd()).as_posix()
    except ValueError:
        return caminho.as_posix()


# Jobs do CI que um PR de raia auxiliar consegue reprovar sozinho. As raias
# auxiliares só escrevem documentação (regra 8 do conferir_pr): se o PR delas
# falha em outro job (testes, smoke), a falha veio da `main`, não do PR.
JOBS_DA_RAIA = frozenset({"disciplina"})
RAIAS_AUXILIARES = frozenset({REVISAO, ESPECIFICACAO, VERIFICACAO})


def jobs_que_falharam(ci: str) -> set[str]:
    """Os jobs de um status `falhou: a, b` do estado_github."""
    texto = str(ci or "")
    if not texto.startswith("falhou"):
        return set()
    _, _, nomes = texto.partition(":")
    return {n.strip() for n in nomes.split(",") if n.strip()}


def falha_herdada(p: dict[str, Any]) -> bool:
    """PR de raia auxiliar que falhou num job que ele não tem como reprovar.

    Em 19/11 um teste dependente do relógio real quebrou a `main`. O PR
    `revisão:` aberto (só `docs/`) falhou no job `test`, o `papel` mandou o
    Revisor destravá-lo, o Revisor não pode mexer em código e a fila parou.
    """
    if p.get("raia") not in RAIAS_AUXILIARES:
        return False
    return bool(jobs_que_falharam(str(p.get("ci", ""))) - JOBS_DA_RAIA)


def main_quebrada(prs: list[dict[str, Any]]) -> dict[str, Any] | None:
    """O primeiro PR de raia auxiliar cuja falha de CI só pode vir da `main`."""
    return next((p for p in prs if falha_herdada(p)), None)


def pr_travado(raia: str, prs: list[dict[str, Any]]) -> dict[str, Any] | None:
    """O PR aberto da raia, se o CI falhou ou há conflito: ninguém mais o salva.

    Falha herdada da `main` não conta: ela é da raia de desenvolvimento, e a
    raia auxiliar não tem como corrigi-la.
    """
    for p in prs:
        if p.get("raia") != raia:
            continue
        if p.get("merge") == "dirty":
            return p
        if str(p.get("ci", "")).startswith("falhou") and not falha_herdada(p):
            return p
    return None


def _consertar_main(p: dict[str, Any]) -> str:
    jobs = ", ".join(sorted(jobs_que_falharam(str(p.get("ci", ""))) - JOBS_DA_RAIA))
    return (
        f"O PR #{p['numero']} ({p.get('raia')}) só mexe em documentação e falhou "
        f"no CI em `{jobs}`: a falha vem da `main`. A entrega desta sessão é "
        "consertar a `main` (Passo 1): reproduza com `make verify` na "
        "`origin/main`, ache a causa raiz e abra um PR `fix:` com teste de "
        "regressão (cite a issue do bug, se houver, com `Closes #N`). Nunca "
        "apague, pule nem afrouxe o teste que falha. Não mexa no PR da raia: "
        "com a `main` consertada, ele passa ao trazer a `main`."
    )


def _com_pr(raia: str, prs: list[dict[str, Any]]) -> bool:
    return any(p.get("raia") == raia for p in prs)


def _destravar(p: dict[str, Any]) -> str:
    return (
        f"O PR #{p['numero']} desta raia está parado (CI: {p.get('ci')}, merge: "
        f"{p.get('merge')}). A tarefa da sessão é destravá-lo na branch dele "
        f"(`{p.get('branch')}`), pela skill `devagent/skills/destravar-pr.md`. "
        "Não abra PR novo."
    )


def trabalho_do_desenvolvimento(
    prontas: list[Path],
    issues: list[dict[str, Any]],
    prs: list[dict[str, Any]],
    producao_quebrada: bool = False,
) -> str:
    """Por que a sessão é do desenvolvedor; vazio se ele não tem trabalho de produto.

    Passos 5 e 6 não contam: eles existem para a volta em que o resto está em
    dia, não para ocupar a sessão enquanto outra raia segura a fila.
    """
    if any(p.get("do_agente") for p in prs):
        return "Existe PR aberto da raia de desenvolvimento."
    if main_quebrada(prs):
        return "A main está quebrada."
    if producao_quebrada or producao_pendente(issues):
        return "A produção acusa problema."
    if issue_prioritaria(issues):
        return "Existe issue `prioridade` aberta."
    fila = fila_do_desenvolvimento(prontas)
    if fila and not tentativas_da_spec(fila[0], issues):
        return "Há spec revisada na fila."
    return ""


def alvo_do_revisor(
    prontas: list[Path],
    issues: list[dict[str, Any]],
    prs: list[dict[str, Any]],
    raiz: Path | None = None,
) -> str:
    travado = pr_travado(REVISAO, prs)
    if travado:
        return _destravar(travado)
    if _com_pr(REVISAO, prs):
        return ""
    dividir = spec_para_dividir(prontas, issues)
    if dividir:
        spec, falhas = dividir
        citadas = ", ".join(f"#{n}" for n in falhas)
        fecha = " ".join(f"Closes #{n}" for n in falhas)
        return (
            f"A tarefa desta sessão é dividir {_relativo(spec, raiz)}: ela teve "
            f"tentativa fechada pelo guardião ({citadas}). Leia a issue, divida a "
            "spec em partes menores (cada parte já revisada), marque a original "
            "como `draft`, diga nela para onde foi cada parte e ponha no corpo do "
            f"PR: {fecha}. Não toque em nenhuma outra spec."
        )
    fila = fila_da_revisao(prontas)
    if not fila:
        return ""
    return (
        f"A spec a revisar nesta sessão é {_relativo(fila[0], raiz)}. Não toque "
        "em nenhuma outra spec."
    )


def alvo_do_especificador(
    prontas: list[Path], prs: list[dict[str, Any]], raiz: Path | None = None
) -> str:
    travado = pr_travado(ESPECIFICACAO, prs)
    if travado:
        return _destravar(travado)
    if _com_pr(ESPECIFICACAO, prs) or len(prontas) > FILA_PARA_ESPECIFICAR:
        return ""
    return (
        f"A fila tem {len(prontas)} spec(s) ready. Para a spec nova desta "
        f"sessão, use o número {proximo_numero(raiz)}: ele está reservado para ela."
    )


def desde_a_ultima_verificacao(raiz: Path | None = None) -> datetime:
    """Hora do último relatório do Verificador, limitada à janela de 24 h."""
    agora = datetime.now(timezone.utc)
    piso = agora - JANELA_DA_VERIFICACAO
    pasta = (raiz or Path.cwd()) / PASTA_VERIFICACAO / "relatorios"
    datas = []
    if pasta.is_dir():
        for p in pasta.glob("*.md"):
            m = RELATORIO.search(p.name)
            if m:
                datas.append(datetime(*map(int, m.groups()), tzinfo=timezone.utc))
    return max([piso, *datas])


# Linha de patch que mexe numa constante de limite (spec 139).
PADRAO_SENSOR = re.compile(
    r"^[+-].*\b\w*(MAXIM[AO]|LIMITE|TOLERANCIA|TETO)\w*\s*=", re.MULTILINE
)
# Quantos merges recentes o alvo do Verificador lista, além dos `[sensor]`.
MAXIMO_DE_MERGES_NO_ALVO = 15
# Teto de páginas (de 50 PRs) na busca dos merges do período.
MAXIMO_DE_PAGINAS = 5


def github_get(caminho: str) -> Any:
    """GET na API do GitHub (o mesmo `_get` do estado_github, importado tarde)."""
    from devagent import estado_github

    return estado_github._get(caminho)


def _repositorio() -> str:
    from devagent.config import PROJETO

    return str(PROJETO["repositorio"])


def _quando(texto: str) -> datetime:
    return datetime.fromisoformat(texto.replace("Z", "+00:00"))


def merges_do_desenvolvimento(desde: datetime) -> list[dict[str, Any]]:
    """PRs da raia de desenvolvimento mesclados depois de `desde`, mais novos antes.

    Vale qualquer autor, inclusive pessoas: o título é que diz a raia (spec
    139). A busca percorre `state=closed` por atualização até a primeira
    página cujo PR mais antigo é anterior a `desde`, com teto de páginas.
    """
    if desde.tzinfo is None:
        desde = desde.replace(tzinfo=timezone.utc)
    repo = _repositorio()
    merges: list[dict[str, Any]] = []
    vistos: set[int] = set()
    for pagina in range(1, MAXIMO_DE_PAGINAS + 1):
        try:
            prs = github_get(
                f"/repos/{repo}/pulls?state=closed&sort=updated&direction=desc"
                f"&per_page=50&page={pagina}"
            )
        except (OSError, ValueError):
            break
        if not prs or not isinstance(prs, list):
            break
        for pr in prs:
            numero = pr.get("number")
            if numero in vistos or not pr.get("merged_at"):
                continue
            if (
                _quando(pr["merged_at"]) > desde
                and raia_do_titulo(pr.get("title") or "") == DESENVOLVIMENTO
            ):
                merges.append(pr)
                if numero is not None:
                    vistos.add(numero)
        atualizados = [_quando(pr["updated_at"]) for pr in prs if pr.get("updated_at")]
        if atualizados and min(atualizados) < desde:
            break
    merges.sort(key=lambda pr: _quando(pr["merged_at"]), reverse=True)
    return merges


def sensor_do_pr(numero: int) -> tuple[bool, bool]:
    """(é sensor, falhou ao ler os arquivos) de um PR.

    É sensor o PR que altera arquivo em `auditoria/` ou cujo patch adiciona ou
    remove linha casando PADRAO_SENSOR (spec 139). Falha na consulta não
    derruba nada: o PR entra sem marca.
    """
    try:
        arquivos = github_get(f"/repos/{_repositorio()}/pulls/{numero}/files")
    except Exception:  # noqa: BLE001 - qualquer falha vira "não consultados"
        return False, True
    if not isinstance(arquivos, list):
        return False, True
    for arq in arquivos:
        nome = arq.get("filename") or ""
        if nome.startswith("auditoria/") or "/auditoria/" in nome:
            return True, False
        if PADRAO_SENSOR.search(arq.get("patch") or ""):
            return True, False
    return False, False


def lista_do_verificador(merges: list[dict[str, Any]]) -> str:
    """O que o Verificador examina: sensores primeiro, sem corte silencioso.

    Traz os MAXIMO_DE_MERGES_NO_ALVO mais recentes mais todo `[sensor]`; o que
    sobra é contado na frase final (spec 139).
    """
    if not merges:
        return ""
    info = [(pr, *sensor_do_pr(pr["number"])) for pr in merges]
    escolhidos = {pr["number"] for pr in merges[:MAXIMO_DE_MERGES_NO_ALVO]} | {
        pr["number"] for pr, sensor, _ in info[MAXIMO_DE_MERGES_NO_ALVO:] if sensor
    }
    omitidos = len(merges) - len(escolhidos)
    na_lista = [i for i in info if i[0]["number"] in escolhidos]
    ordenados = [i for i in na_lista if i[1]] + [i for i in na_lista if not i[1]]
    itens = []
    for pr, sensor, erro in ordenados:
        if sensor:
            itens.append(f"#{pr['number']} [sensor] ({pr['title']})")
        elif erro:
            itens.append(f"#{pr['number']} ({pr['title']}) (arquivos não consultados)")
        else:
            itens.append(f"#{pr['number']} ({pr['title']})")
    texto = "Verifique o que estes PRs levaram à main: " + ", ".join(itens) + "."
    if omitidos > 0:
        texto += f" +{omitidos} PRs omitidos; liste com git log --merges."
    return texto


def alvo_do_verificador(merges: list[dict[str, Any]], prs: list[dict[str, Any]]) -> str:
    """`merges`: PRs que a raia de desenvolvimento levou à main no período."""
    travado = pr_travado(VERIFICACAO, prs)
    if travado:
        return _destravar(travado)
    if _com_pr(VERIFICACAO, prs) or not merges:
        return ""
    return lista_do_verificador(merges)


def entregas_sem_spec(titulos: list[str]) -> int:
    """Quantas entregas seguidas da raia de desenvolvimento não fecharam spec.

    `titulos` vem do mais novo para o mais antigo. PR de outra raia não conta
    nem interrompe a contagem.
    """
    n = 0
    for titulo in titulos:
        if raia_do_titulo(titulo) != DESENVOLVIMENTO:
            continue
        if ENTREGA_DE_SPEC.match(titulo.strip()):
            break
        n += 1
    return n


def decidir(
    prontas: list[Path],
    issues: list[dict[str, Any]],
    prs: list[dict[str, Any]],
    producao_quebrada: bool = False,
    titulos_da_main: list[str] | None = None,
    raiz: Path | None = None,
) -> Papel:
    """O papel da sessão que ninguém nomeou (decisão pura, testável).

    O desenvolvedor vem primeiro sempre que tem trabalho de produto. Sem ele,
    a sessão assume a raia que segura a fila: revisão antes de especificação,
    porque spec escrita e não revisada ainda não é trabalho para ninguém.
    """
    motivo = trabalho_do_desenvolvimento(prontas, issues, prs, producao_quebrada)
    quebra = main_quebrada(prs)
    if motivo and quebra and not any(p.get("do_agente") for p in prs):
        return Papel(DESENVOLVEDOR, motivo, _consertar_main(quebra))
    if motivo:
        return Papel(DESENVOLVEDOR, motivo)
    alvo = alvo_do_revisor(prontas, issues, prs, raiz)
    if alvo:
        return Papel(
            REVISOR,
            "o desenvolvimento não tem trabalho de produto e a fila espera a "
            "raia de revisão.",
            alvo,
        )
    alvo = alvo_do_especificador(prontas, prs, raiz)
    if alvo:
        return Papel(
            ESPECIFICADOR,
            "o desenvolvimento não tem trabalho de produto e a fila de specs "
            "está no fim.",
            alvo,
        )
    paradas = entregas_sem_spec(titulos_da_main or [])
    if prontas and paradas >= LIMITE_SEM_SPEC:
        return Papel(
            DESENVOLVEDOR,
            f"FILA TRAVADA: há {len(prontas)} spec(s) ready e as últimas {paradas} "
            "entregas do desenvolvimento não fecharam nenhuma.",
            "A entrega desta sessão é destravar a fila, não outra melhoria: ache "
            "o que a segura (CICLO.md, *Fila travada*). Causa no repositório se "
            "corrige agora; causa fora dele vai uma única vez para a seção "
            "*Bloqueios* do estado do sistema. Com o bloqueio já registrado, "
            "encerre sem PR.",
        )
    return Papel(DESENVOLVEDOR, "")


def para_persona(
    persona: str,
    prontas: list[Path],
    issues: list[dict[str, Any]],
    prs: list[dict[str, Any]],
    merges: list[dict[str, Any]] | None = None,
    raiz: Path | None = None,
) -> Papel:
    """O alvo da persona que a tarefa nomeou; alvo vazio = encerrar sem PR."""
    if persona == REVISOR:
        alvo = alvo_do_revisor(prontas, issues, prs, raiz)
    elif persona == ESPECIFICADOR:
        alvo = alvo_do_especificador(prontas, prs, raiz)
    elif persona == VERIFICADOR:
        alvo = alvo_do_verificador(merges or [], prs)
    else:
        raise ValueError(f"persona desconhecida: {persona}")
    return Papel(persona, "a tarefa nomeou a persona.", alvo)


def titulos_da_main(desde: datetime | None = None, limite: int = 40) -> list[str]:
    """Títulos dos commits da main, do mais novo para o mais antigo."""
    comando = ["git", "log", "origin/main", "--format=%s", f"-{limite}"]
    if desde:
        comando.append(f"--since={desde.isoformat()}")
    try:
        saida = subprocess.run(comando, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return []
    return [t for t in saida.stdout.splitlines() if t.strip()]


# ---------------------------------------------------------------------------
# Conferência antes do PR. O alvo é decidido no início da sessão, e uma sessão
# leva de 10 a 15 minutos. Em 14/11 21:38 a tarefa do Revisor escolheu a spec
# 150 um minuto antes de a sessão do ciclo abrir o #847 com a mesma revisão: as
# duas reescreveram a mesma spec. A sessão confere de novo, contra a `main` e
# os PRs abertos de agora, imediatamente antes de abrir o PR.

RAIA_DE = {
    DESENVOLVEDOR: DESENVOLVIMENTO,
    REVISOR: REVISAO,
    ESPECIFICADOR: ESPECIFICACAO,
}
NUMERO_NO_TITULO = r"(?<![\d#])0*{n}(?![\d])"


def _cita(titulo: str, numero: str) -> bool:
    base = re.match(r"0*(\d+)([a-z]*)", numero)
    if not base:
        return False
    alvo = base.group(1) + base.group(2)
    return bool(re.search(NUMERO_NO_TITULO.format(n=re.escape(alvo)), titulo))


def alvo_ocupado(
    persona: str,
    numero: str,
    prs: list[dict[str, Any]],
    texto_na_main: str | None,
) -> str:
    """Por que o alvo já não é desta sessão; vazio se ainda está livre (puro).

    `texto_na_main` é a spec como está na `main` agora (None se não existe).
    """
    raia = RAIA_DE[persona]
    for p in prs:
        if p.get("raia") != raia:
            continue
        if raia != DESENVOLVIMENTO:
            return (
                f"já existe PR aberto da raia: #{p['numero']} ({p['titulo']}). "
                "Cada raia tem um PR aberto por vez."
            )
        if _cita(p.get("titulo", ""), numero):
            return f"o PR #{p['numero']} ({p['titulo']}) já cuida da spec {numero}."
    if persona == ESPECIFICADOR:
        if texto_na_main is not None:
            return f"o número {numero} já está ocupado na main."
        return ""
    if texto_na_main is None:
        return f"a spec {numero} não existe mais na main."
    if persona == REVISOR and REVISADA_NO_CABECALHO.search(texto_na_main):
        return f"a spec {numero} já foi revisada na main."
    status = re.search(r"^status:\s*([\w-]+)", texto_na_main, re.MULTILINE)
    if not status or status.group(1) != "ready":
        estado = status.group(1) if status else "sem status"
        return f"a spec {numero} está `{estado}` na main, não `ready`."
    return ""


REVISADA_NO_CABECALHO = re.compile(r"^revisada:\s*\S", re.MULTILINE)


def spec_na_main(numero: str, pasta: str = "docs/specs") -> str | None:
    """O texto da spec `numero` na origin/main, sem olhar a árvore de trabalho."""
    try:
        nomes = subprocess.run(
            ["git", "ls-tree", "--name-only", "origin/main", f"{pasta}/"],
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout.split()
    except (OSError, subprocess.SubprocessError):
        return None
    m = re.match(r"0*(\d+)([a-z]*)", numero)
    if not m:
        return None
    padrao = re.compile(rf"/0*{m.group(1)}{m.group(2)}-[^/]*\.md$")
    for nome in nomes:
        if padrao.search(nome):
            return subprocess.run(
                ["git", "show", f"origin/main:{nome}"],
                capture_output=True,
                text=True,
                timeout=30,
            ).stdout
    return None


def conferir(persona: str, numero: str) -> int:
    from devagent import estado_github

    subprocess.run(["git", "fetch", "-q", "origin"], timeout=120, check=False)
    try:
        prs = estado_github.coletar()["prs"]
    except OSError as exc:
        print(f"Não consegui ler os PRs abertos ({exc}): encerre sem PR.")
        return 1
    motivo = alvo_ocupado(persona, numero, prs, spec_na_main(numero))
    if motivo:
        print(
            f"Alvo ocupado: {motivo} Outra sessão chegou antes. Descarte as "
            "alterações e encerre sem PR."
        )
        return 1
    print(f"Alvo livre: pode abrir o PR da spec {numero}.")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args[:1] == ["conferir"]:
        if len(args) != 3 or args[1].lower() not in RAIA_DE:
            print(
                "Uso: python -m devagent.papel conferir "
                "<desenvolvedor | revisor | especificador> <número da spec>",
                file=sys.stderr,
            )
            return 2
        return conferir(args[1].lower(), args[2])
    persona = args[0].lower() if args else ""
    if persona and persona not in RAIA_DA_PERSONA:
        print(
            f"Uso: python -m devagent.papel [{' | '.join(RAIA_DA_PERSONA)}]",
            file=sys.stderr,
        )
        return 2

    from devagent import estado_github, saude

    try:
        estado = estado_github.coletar()
    except OSError as exc:
        print(f"Falha ao consultar o GitHub: {exc}", file=sys.stderr)
        return 3
    prontas = specs_prontas()

    if persona:
        merges = (
            merges_do_desenvolvimento(desde_a_ultima_verificacao())
            if persona == VERIFICADOR
            else None
        )
        papel = para_persona(persona, prontas, estado["issues"], estado["prs"], merges)
        if not papel.alvo:
            print(
                f"Sem trabalho para o {NOME[persona]} nesta volta: encerre sem PR "
                "e sem commit."
            )
            return 0
        print(papel.alvo)
        return 0

    try:
        quebrada = bool(saude.pedem_correcao(saude.ler(espera=90)))
    except saude.Indisponivel:
        quebrada = False
    papel = decidir(
        prontas, estado["issues"], estado["prs"], quebrada, titulos_da_main()
    )
    print(f"Papel: {NOME[papel.persona]}")
    if papel.frase():
        print(papel.frase())
    return 0


if __name__ == "__main__":
    sys.exit(main())
