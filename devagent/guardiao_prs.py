"""Guardião de PRs: impede que PRs do agente fiquem travados.

Roda no GitHub Actions (workflow pr-guardiao.yml) com o gh CLI autenticado:
    python -m devagent.guardiao_prs ...

Modos:
    --ci-falhou BRANCH --run-id ID   CI falhou num PR: cobra o Jules ou fecha o PR
    --varredura                      conflitos, PRs sem reação, substituídos, branches órfãs

Regras (mantenha em sincronia com devagent/skills/destravar-pr.md):
    - CI falhou: comenta @jules com o log, até MAX_TENTATIVAS. Depois fecha o PR.
    - Especialista sem achado: PR de Sentinel, Palette ou Bolt vazio ou só com
      o diário fecha sem issue; não é trabalho perdido (ADRs 019 e 020).
    - Falha irrecuperável: PR vazio ou só com registros de execução não tem
      nada a corrigir na branch (a sessão perdeu o trabalho). Fecha na hora,
      sem cobrar o agente, e abre `tentativa-falhou` (ADR 018). Cobrar só
      gerava sessões filhas com PRs vazios (#402 e #403, em 22/10).
    - Sem reação: se o guardião cobrou e não houve commit novo em SEM_REACAO_HORAS, fecha.
    - Conflito pequeno (<= CONFLITO_MAX_ARQUIVOS e <= CONFLITO_MAX_LINHAS): pede ao Jules
      para resolver. Conflito grande: fecha o PR; o próximo ciclo refaz a partir da main.
    - PR cujo corpo diz "Substitui #N": fecha o #N.
    - Issue citada com Closes/Fixes/Resolves num PR mergeado nos últimos 7 dias: fecha.
    - Ao fechar, abre issue `tentativa-falhou` com o motivo e a spec do PR, para o
      próximo ciclo aprender. Exceção: se tudo o que o PR muda já chegou à main
      (sobram só registros de execução), fecha como absorvido e não abre issue (ADR 014).
    - `tentativa-falhou` órfã fecha: a spec citada já está `done` na main, ou a
      issue não cita spec nenhuma e por isso nenhum passo do ciclo a lê (ADR 020),
      ou as specs citadas estão `draft` ou não existem (ADR 024).
    - Antes do merge (--antes-do-merge): PR que altera spec que a main já
      alterou depois que a branch saiu dela fecha como redundante (ADR 024).
    - Só PRs e branches do Jules: PR ou branch de pessoa fica intocado.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import tempfile
from datetime import datetime, timedelta, timezone
from typing import Any

from devagent.conferir_pr import FECHA_ISSUE, PADRAO_REGISTROS, documentos, status_de
from devagent.config import VERIFICACAO
from devagent.raias import do_agente, do_desenvolvimento

MAX_TENTATIVAS = 3
SEM_REACAO_HORAS = 3
CONFLITO_MAX_ARQUIVOS = 3
CONFLITO_MAX_LINHAS = 40
ORFA_HORAS = 24

MARCA_CI = "<!-- guardiao:ci -->"


def retomada(branch: str) -> str:
    """Instrução de retomada que vai em toda cobrança ao agente.

    O ambiente do agente pode ser reiniciado entre a abertura do PR e a
    cobrança. Sem esta instrução, ele volta para a `main` limpa, tenta refazer
    o trabalho do zero e para perguntando se deve continuar (ADR 009).
    """
    return (
        "**Se o seu ambiente foi reiniciado e perdeu as alterações**, não recomece "
        "da `main` nem recrie a spec: o trabalho já feito está nesta branch. Rode "
        f"`git fetch origin && git checkout -B {branch} origin/{branch}` e continue "
        "dali. Não faça perguntas nem peça confirmação: ninguém vai responder."
    )


MARCA_CONFLITO = "<!-- guardiao:conflito -->"


def sh(*cmd: str, check: bool = True) -> str:
    r = subprocess.run(cmd, capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)}\n{r.stderr}")
    return r.stdout


def gh_json(*args: str) -> Any:
    return json.loads(sh("gh", *args))


def agora() -> datetime:
    return datetime.now(timezone.utc)


def data(iso: str) -> datetime:
    return datetime.fromisoformat(iso.replace("Z", "+00:00"))


def prs_do_agente() -> list[dict[str, Any]]:
    """PRs abertos pelo Jules, menos os do auditor.

    PR de pessoa (o dono do produto) não é cobrado nem fechado: o guardião
    cuidaria dele como se fosse do agente e abriria `tentativa-falhou` (ADR 024).
    """
    campos = "number,title,headRefName,headRefOid,body,labels,createdAt,url,author"
    prs = gh_json("pr", "list", "--state", "open", "--json", campos, "--limit", "50")
    return [
        p
        for p in prs
        if not p["title"].startswith("auditoria:")
        and do_agente((p.get("author") or {}).get("login"))
    ]


def comentarios(numero: int) -> list[dict[str, Any]]:
    return gh_json("pr", "view", str(numero), "--json", "comments")["comments"]


def data_ultimo_commit(numero: int) -> datetime:
    commits = gh_json("pr", "view", str(numero), "--json", "commits")["commits"]
    return data(commits[-1]["committedDate"])


def comentar(numero: int, corpo: str) -> None:
    sh("gh", "pr", "comment", str(numero), "--body", corpo)


def pendentes_fora_da_main(ref: str, main: str = "origin/main") -> list[str]:
    """Arquivos cuja mudança no PR nunca chegou à main.

    Uma mudança conta como absorvida se o diff do arquivo (do ponto de
    divergência até a ponta do PR) já esteve aplicado em algum commit da main
    depois da divergência. Olhar só a ponta da main não basta: em 19/10 o #344
    foi fechado por conflito porque o #345 mexeu de novo nos mesmos arquivos,
    mas o conteúdo já tinha entrado pelo #343. Usa um índice temporário para
    não tocar na árvore de trabalho.
    """
    base = sh("git", "merge-base", main, ref).strip()
    arquivos = sh("git", "diff", "--name-only", base, ref).split()
    patches = {a: sh("git", "diff", base, ref, "--", a) for a in arquivos}
    pendentes = {a for a, p in patches.items() if p}
    commits = sh("git", "rev-list", "--first-parent", f"{base}..{main}").split()
    indice = os.path.join(tempfile.mkdtemp(prefix="guardiao-"), "index")
    env = {**os.environ, "GIT_INDEX_FILE": indice}
    for commit in commits:
        if not pendentes:
            break
        subprocess.run(["git", "read-tree", commit], env=env, check=True)
        for arq in sorted(pendentes):
            r = subprocess.run(
                ["git", "apply", "-R", "--check", "--cached"],
                input=patches[arq],
                text=True,
                capture_output=True,
                env=env,
            )
            if r.returncode == 0:
                pendentes.discard(arq)
    return sorted(pendentes)


def absorvido_pela_main(branch: str) -> bool:
    """True se só faltam na main registros de execução (docs/runs/, .jules/)."""
    try:
        sh("git", "fetch", "-q", "origin", "main", branch)
        faltam = pendentes_fora_da_main(f"origin/{branch}")
    except (RuntimeError, subprocess.CalledProcessError) as erro:
        print(f"::warning::não deu para comparar {branch} com a main: {erro}")
        return False
    return all(a.startswith(PADRAO_REGISTROS) for a in faltam)


def arquivos_do_pr(numero: int) -> list[str] | None:
    """Arquivos alterados pelo PR, pela API REST. None se não deu para ler."""
    try:
        dados = gh_json(
            "api", f"repos/{{owner}}/{{repo}}/pulls/{numero}/files?per_page=100"
        )
    except (RuntimeError, json.JSONDecodeError):
        return None
    return [d["filename"] for d in dados]


def motivo_irrecuperavel(arquivos: list[str] | None, corpo: str = "") -> str:
    """Motivo para fechar sem cobrar, ou "" se o PR tem trabalho a corrigir.

    PR vazio ou só com registros de execução não tem código na branch: a
    sessão perdeu o que fez. Cobrar o agente não traz o trabalho de volta.
    Exceção, como na regra 6 do conferir_pr: PR só de registro que fecha
    issues (`Closes #N`) é entrega legítima.
    """
    if arquivos is None:
        return ""
    if not arquivos:
        return (
            "o PR não altera nenhum arquivo. Não há nada a corrigir na branch; "
            "a sessão que o abriu não tinha o trabalho."
        )
    if all(a.startswith(PADRAO_REGISTROS) for a in arquivos) and not FECHA_ISSUE.search(
        corpo
    ):
        return (
            "o PR só traz registros de execução ("
            + ", ".join(sorted(arquivos))
            + "). O código descrito neles não chegou à branch: a sessão perdeu o "
            "trabalho. Se a spec for grande, a próxima tentativa deve dividi-la."
        )
    return ""


# Título dos PRs dos especialistas (devagent/agents/especialistas.md).
ESPECIALISTA = re.compile(r"(?:^|\s)(Sentinel|Palette|Bolt):")


def sem_achado_de_especialista(pr: dict[str, Any], arquivos: list[str] | None) -> bool:
    """PR de especialista vazio ou só com o diário: a varredura não achou nada.

    Não é sessão que perdeu o trabalho. Em 22/10 o #406 (Sentinel, varredura
    limpa) foi fechado como trabalho perdido e a issue #407 mandou "dividir a
    spec" de uma tarefa que não tem spec (ADR 019). Em 23/10 o #426 (Sentinel,
    nenhum arquivo) abriu a #427, que nenhum passo do ciclo lê (ADR 020). Fecha
    sem abrir `tentativa-falhou`; a regra 7 dos especialistas já diz para não
    abrir esse PR.
    """
    if arquivos is None or not ESPECIALISTA.search(pr.get("title") or ""):
        return False
    if FECHA_ISSUE.search(pr.get("body") or ""):
        return False
    return all(a.startswith(PADRAO_REGISTROS) for a in arquivos)


def fechar_sem_achado(pr: dict[str, Any]) -> None:
    numero = pr["number"]
    comentar(
        numero,
        "Fechando este PR: a varredura do especialista não achou nada a mudar e "
        "o PR não traz nada além do diário. Não há trabalho perdido nem spec a refazer, então "
        "não abro issue `tentativa-falhou`. Pela regra 7 de "
        "`devagent/agents/especialistas.md`, sem achado a sessão encerra sem PR.",
    )
    sh("gh", "pr", "close", str(numero), "--delete-branch", check=False)
    print(f"PR #{numero} fechado: especialista sem achado")


# Spec citada num texto: marcador do guardião, caminho do arquivo ou "spec 076b".
SPEC_NO_TEXTO = re.compile(
    r"(?i)(?:<!-- spec: |specs/|\bspec\s+`?)(\d{1,4}[a-z]?)(?![a-z0-9])"
)
SPEC_NO_ARQUIVO = re.compile(r"(?:^|/)(\d{1,4}[a-z]?)-[^/]*\.md$")


def chave_spec(spec: str) -> str:
    """ "076b", "76B" e "0076b" são a mesma spec."""
    m = re.fullmatch(r"(\d+)([a-z]?)", spec.lower())
    return f"{int(m.group(1))}{m.group(2)}" if m else spec.lower()


def specs_citadas(texto: str, arquivos: list[str] | None = None) -> list[str]:
    """Specs citadas no texto ou alteradas pelo PR, sem repetição.

    "spec 076b", "specs/076b-x.md" e o marcador `<!-- spec: 076b -->` contam;
    "#76" e números soltos não.
    """
    achadas = [m.lower() for m in SPEC_NO_TEXTO.findall(texto or "")]
    pasta = documentos()["specs"].rstrip("/") + "/"
    for arq in arquivos or []:
        if arq.startswith(pasta):
            m = SPEC_NO_ARQUIVO.search(arq)
            if m:
                achadas.append(m.group(1).lower())
    unicas: dict[str, str] = {}
    for spec in achadas:
        unicas.setdefault(chave_spec(spec), spec)
    return list(unicas.values())


def specs_do_pr(pr: dict[str, Any], arquivos: list[str] | None) -> list[str]:
    return specs_citadas(
        f"{pr.get('title') or ''}\n{pr.get('body') or ''}\n{pr.get('headRefName') or ''}",
        arquivos,
    )


def fechar(
    pr: dict[str, Any], motivo: str, detalhe: str = "", registrar: bool = False
) -> None:
    """Fecha o PR. `registrar` abre a issue mesmo se a main já tem tudo."""
    numero = pr["number"]
    if (
        not registrar
        and pr.get("headRefName")
        and absorvido_pela_main(pr["headRefName"])
    ):
        comentar(
            numero,
            f"Fechando este PR: {motivo}\n\n"
            "Nada se perde: tudo o que ele muda já está na `main` (sobram no "
            "máximo registros de execução). Não há trabalho a refazer, então "
            "não abro issue `tentativa-falhou`.",
        )
        sh("gh", "pr", "close", str(numero), "--delete-branch", check=False)
        print(f"PR #{numero} fechado como absorvido pela main: {motivo}")
        return
    if not do_desenvolvimento(pr.get("title") or ""):
        # Raia paralela (ADR 021): não há spec a dividir nem trabalho que o
        # desenvolvimento deva refazer. A própria raia recomeça na próxima
        # rodada, a partir da main atualizada.
        comentar(
            numero,
            f"Fechando este PR: {motivo}\n\n"
            "Ele é de uma raia paralela; a próxima rodada abre uma sessão nova "
            "dessa raia a partir da `main` atualizada. Sem issue `tentativa-falhou`.",
        )
        sh("gh", "pr", "close", str(numero), "--delete-branch", check=False)
        print(f"PR #{numero} da raia paralela fechado: {motivo}")
        return
    corpo = (
        f"Fechando este PR: {motivo}\n\n"
        "O trabalho não se perde: a spec continua `ready` na `main`, e o próximo "
        "ciclo do agente refaz a partir da `main` atualizada. O motivo ficou "
        "registrado numa issue `tentativa-falhou` para não repetir o erro."
    )
    comentar(numero, corpo)
    sh("gh", "pr", "close", str(numero), "--delete-branch", check=False)
    sh(
        "gh",
        "label",
        "create",
        "tentativa-falhou",
        "--color",
        "D93F0B",
        "--description",
        "PR do agente fechado pelo guardião",
        check=False,
    )
    specs = specs_do_pr(pr, arquivos_do_pr(numero))
    # "spec 076b" por extenso: é o que o fila_specs procura para mandar dividir
    # a spec (ADR 018); o marcador é o que o guardião procura para fechar a
    # issue quando a spec virar `done` (ADR 020).
    linha_specs = (
        "**Spec:** "
        + ", ".join(f"spec {s}" for s in specs)
        + "\n"
        + "".join(f"<!-- spec: {s} -->" for s in specs)
        + "\n\n"
        if specs
        else ""
    )
    corpo_issue = (
        f"O guardião fechou {pr['url']} ({pr['title']}).\n\n"
        f"**Motivo:** {motivo}\n\n"
        + linha_specs
        + (
            f"<details><summary>Detalhe</summary>\n\n```\n{detalhe[-6000:]}\n```\n</details>\n\n"
            if detalhe
            else ""
        )
        + "Antes de refazer este trabalho, leia esta issue e evite o mesmo erro. "
        "O PR que concluir o trabalho deve conter `Closes` para esta issue."
    )
    sh(
        "gh",
        "issue",
        "create",
        "--title",
        f"Tentativa fechada: {pr['title']}",
        "--label",
        "tentativa-falhou",
        "--body",
        corpo_issue,
    )
    print(f"PR #{numero} fechado: {motivo}")


def ci_falhou(branch: str, run_id: str) -> None:
    pr = next((p for p in prs_do_agente() if p["headRefName"] == branch), None)
    if not pr:
        print(f"Nenhum PR do agente aberto para {branch}")
        return
    log = sh("gh", "run", "view", run_id, "--log-failed", check=False)
    log = "\n".join(log.splitlines()[-120:])
    arquivos = arquivos_do_pr(pr["number"])
    if sem_achado_de_especialista(pr, arquivos):
        fechar_sem_achado(pr)
        return
    irrecuperavel = motivo_irrecuperavel(arquivos, pr.get("body") or "")
    if irrecuperavel:
        fechar(pr, irrecuperavel, log, registrar=True)
        return
    tentativas = sum(MARCA_CI in c["body"] for c in comentarios(pr["number"]))
    if tentativas >= MAX_TENTATIVAS:
        fechar(pr, f"o CI falhou {tentativas + 1} vezes seguidas.", log)
        return
    comentar(
        pr["number"],
        f"{MARCA_CI}\n@jules o CI falhou neste PR (cobrança {tentativas + 1} de "
        f"{MAX_TENTATIVAS}). Corrija **nesta mesma branch**, sem abrir PR novo. "
        f"Reproduza localmente com `{VERIFICACAO['verify']}` e `{VERIFICACAO['smoke']}` "
        "(veja `devagent/skills/destravar-pr.md`).\n\n"
        f"{retomada(branch)}\n\n"
        f"Se não houver commit novo em {SEM_REACAO_HORAS} h, este PR será fechado.\n\n"
        f"<details><summary>Log da falha</summary>\n\n```\n{log}\n```\n</details>",
    )
    print(f"Cobrança {tentativas + 1} enviada ao PR #{pr['number']}")


def contar_conflito(texto: str) -> tuple[int, int]:
    """Conta as linhas em conflito de um arquivo mesclado no estilo diff3.

    Devolve (reais, acrescimo). Um trecho cuja base está vazia é só acréscimo:
    os dois lados inseriram blocos novos no mesmo ponto e nenhum mexeu no que
    já existia, então a resolução é manter os dois. É o caso típico de dois PRs
    que acrescentam estilos no fim do `tema.css` ou entradas no `STATE.md`
    (#362 contra #358). Esses trechos não medem o tamanho do conflito.
    """
    reais = acrescimo = 0
    secao = None  # "nosso", "base", "deles"
    lados = base = 0
    for linha in texto.splitlines():
        if linha.startswith("<<<<<<<"):
            secao, lados, base = "nosso", 0, 0
        elif secao and linha.startswith("|||||||"):
            secao = "base"
        elif secao and linha.startswith("======="):
            secao = "deles"
        elif secao and linha.startswith(">>>>>>>"):
            if base == 0:
                acrescimo += lados
            else:
                reais += lados
            secao = None
        elif secao == "base":
            base += 1
        elif secao:
            lados += 1
    return reais, acrescimo


def medir_conflito_entre(base: str, ref: str) -> tuple[list[str], int, int] | None:
    """Merge de teste de `ref` em `base`. None = sem conflito.

    Devolve (arquivos, linhas reais, linhas de acréscimo dos dois lados).
    """
    sh("git", "checkout", "-q", "--detach", base)
    r = subprocess.run(
        [
            "git",
            "-c",
            "merge.conflictStyle=diff3",
            "merge",
            "--no-commit",
            "--no-ff",
            ref,
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    try:
        if r.returncode == 0:
            return None
        arquivos = sh("git", "diff", "--name-only", "--diff-filter=U").split()
        reais = acrescimo = 0
        for arq in arquivos:
            try:
                with open(arq, encoding="utf-8", errors="replace") as f:
                    r_arq, a_arq = contar_conflito(f.read())
                reais += r_arq
                acrescimo += a_arq
                if r_arq == 0 and a_arq == 0:
                    reais += CONFLITO_MAX_LINHAS + 1  # removido/renomeado: grande
            except OSError:
                reais += (
                    CONFLITO_MAX_LINHAS + 1
                )  # arquivo removido/binário: conta como grande
        return arquivos, reais, acrescimo
    finally:
        sh("git", "merge", "--abort", check=False)
        sh("git", "reset", "-q", "--hard", check=False)


def medir_conflito(branch: str) -> tuple[list[str], int, int] | None:
    """Faz um merge de teste da branch na main. None = sem conflito."""
    sh("git", "fetch", "-q", "origin", "main", branch)
    return medir_conflito_entre("origin/main", f"origin/{branch}")


PALAVRA_CHAVE = re.compile(
    r"(?i)\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)[: ]+#(\d+)"
)
ISSUES_DE_PRODUCAO = {"deploy-falhou", "producao-incorreta", "sistema-com-problema"}
DIAS_FECHAR_CITADAS = 7


def mensagens_dos_commits(numero: int) -> list[str]:
    """Mensagens completas dos commits de um PR, pela API REST."""
    try:
        commits = gh_json(
            "api", f"repos/{{owner}}/{{repo}}/pulls/{numero}/commits?per_page=100"
        )
    except (RuntimeError, json.JSONDecodeError):
        return []
    return [(c.get("commit") or {}).get("message", "") for c in commits]


def fechar_issues_citadas() -> None:
    """Fecha issues citadas com Closes/Fixes/Resolves em PRs mergeados recentes.

    Reserva do passo equivalente no automerge.yml: cobre merges manuais e
    merges feitos antes de o automerge ter permissão de issues. Issues de
    produção ficam abertas: quem as fecha é a verificação que as abriu.
    """
    desde = (agora() - timedelta(days=DIAS_FECHAR_CITADAS)).strftime("%Y-%m-%d")
    prs = gh_json(
        "pr",
        "list",
        "--state",
        "merged",
        "--search",
        f"merged:>={desde}",
        # Sem o campo commits: o gh o traduz em commits(first:100) com
        # authors(first:100) por commit, e com 100 PRs a consulta GraphQL
        # passa do teto de 500 mil nós do GitHub e é recusada inteira.
        "--json",
        "number,title,body",
        "--limit",
        "100",
    )
    for pr in prs:
        textos = [pr["title"], pr.get("body") or ""] + mensagens_dos_commits(
            pr["number"]
        )
        for n in sorted({int(x) for x in PALAVRA_CHAVE.findall("\n".join(textos))}):
            try:
                issue = gh_json("issue", "view", str(n), "--json", "state,labels")
            except (RuntimeError, json.JSONDecodeError):
                continue  # número de PR, issue inexistente ou sem acesso
            labels = {lbl["name"] for lbl in issue.get("labels", [])}
            if issue.get("state") != "OPEN" or labels & ISSUES_DE_PRODUCAO:
                continue
            sh(
                "gh",
                "issue",
                "close",
                str(n),
                "--comment",
                f"Fechada pelo PR #{pr['number']}, mergeado na main "
                "(fechamento feito pelo guardião).",
                check=False,
            )
            print(f"Issue #{n} fechada (citada no PR #{pr['number']})")


PR_NO_CORPO = re.compile(r"/pull/(\d+)")


def status_das_specs(ref: str = "origin/main") -> dict[str, str]:
    """Status de cada spec em `ref`, pela chave normalizada ("76b": "done").

    Lê do git, não da árvore de trabalho: a varredura troca de branch.
    """
    pasta = documentos()["specs"].rstrip("/")
    nomes = sh("git", "ls-tree", "--name-only", ref, f"{pasta}/").split()
    status: dict[str, str] = {}
    for nome in nomes:
        m = SPEC_NO_ARQUIVO.search(nome)
        if not m:
            continue
        st = status_de(sh("git", "show", f"{ref}:{nome}", check=False))
        if st:
            status[chave_spec(m.group(1))] = st
    return status


def motivo_tentativa_orfa(specs: list[str], status: dict[str, str]) -> str:
    """Motivo para fechar a `tentativa-falhou`, ou "" se ela ainda ensina algo.

    O ciclo só lê `tentativa-falhou` no Passo 4, para a próxima spec da fila
    (ADR 018), e o Passo 6 a exclui. Sem spec, ninguém a lê; com a spec já
    `done`, o trabalho foi entregue e a lição não tem mais a quem servir. Em
    23/10 a #416 (spec 076b, entregue no #414 sem `Closes`) e a #427 (Sentinel
    sem spec) estavam nessas condições (ADR 020).
    """
    if not specs:
        return (
            "esta tentativa não cita spec nenhuma. O ciclo só lê `tentativa-falhou` "
            "ao pegar a próxima spec da fila (Passo 4), então nenhuma sessão "
            "chegaria a ela."
        )
    estados = [status.get(chave_spec(s)) for s in specs]
    lista = ", ".join(f"spec {s}" for s in specs)
    if all(e == "done" for e in estados):
        return (
            f"o trabalho já foi entregue: {lista} está com `status: done` na `main`. "
            "O PR da entrega não trouxe `Closes` para esta issue."
        )
    # Spec dividida (draft) ou que nem existe: nenhuma sessão vai pegá-la da
    # fila, e a lição já foi usada na divisão. Era o caso da #523 (092) e da
    # #550 (093, 122 a 124) em 27/10 (ADR 024).
    if all(e in (None, "draft", "done") for e in estados):
        return (
            f"nenhuma das specs citadas ({lista}) está na fila: estão `draft` "
            "(divididas ou descartadas), `done` ou não existem na `main`."
        )
    return ""


def fechar_tentativas_orfas() -> None:
    """Fecha `tentativa-falhou` que nenhum passo do ciclo vai consumir (ADR 020)."""
    issues = [
        i
        for i in gh_json(
            "api",
            "repos/{owner}/{repo}/issues?state=open&labels=tentativa-falhou&per_page=100",
        )
        if "pull_request" not in i
    ]
    if not issues:
        return
    sh("git", "fetch", "-q", "origin", "main")
    status = status_das_specs()
    for issue in issues:
        if "bloqueado" in {lbl["name"] for lbl in issue.get("labels", [])}:
            continue
        corpo = issue.get("body") or ""
        specs = specs_citadas(f"{issue['title']}\n{corpo}")
        if not specs:
            # Issues antigas não têm o marcador: as specs vêm do PR fechado.
            m = PR_NO_CORPO.search(corpo)
            if m:
                specs = specs_citadas("", arquivos_do_pr(int(m.group(1))))
        motivo = motivo_tentativa_orfa(specs, status)
        if not motivo:
            continue
        sh(
            "gh",
            "issue",
            "close",
            str(issue["number"]),
            "--reason",
            "not planned",
            "--comment",
            f"Fechada pelo guardião: {motivo}",
            check=False,
        )
        print(f"Issue #{issue['number']} fechada: tentativa órfã")


def varredura() -> None:
    # Um passo auxiliar com defeito não pode cegar os outros: de 28/09 a 30/09
    # uma falha aqui derrubou a varredura inteira em toda execução.
    try:
        fechar_issues_citadas()
    except Exception as erro:  # noqa: BLE001
        print(f"::warning::fechar_issues_citadas falhou: {erro}")
    try:
        fechar_tentativas_orfas()
    except Exception as erro:  # noqa: BLE001
        print(f"::warning::fechar_tentativas_orfas falhou: {erro}")
    prs = prs_do_agente()
    fechados: set[int] = set()

    # 1. PRs substituídos
    for pr in prs:
        for n in re.findall(r"[Ss]ubstitui #(\d+)", pr.get("body") or ""):
            alvo = next((p for p in prs if p["number"] == int(n)), None)
            if alvo and alvo["number"] not in fechados:
                comentar(alvo["number"], f"Substituído por #{pr['number']}.")
                sh("gh", "pr", "close", n, "--delete-branch", check=False)
                fechados.add(alvo["number"])

    for pr in prs:
        if pr["number"] in fechados:
            continue
        arquivos = arquivos_do_pr(pr["number"])
        if sem_achado_de_especialista(pr, arquivos):
            fechar_sem_achado(pr)
            continue
        irrecuperavel = motivo_irrecuperavel(arquivos, pr.get("body") or "")
        if irrecuperavel:
            fechar(pr, irrecuperavel, registrar=True)
            continue
        coms = comentarios(pr["number"])
        ultimo_commit = data_ultimo_commit(pr["number"])

        # 2. Cobrança sem reação
        cobrancas = [
            data(c["createdAt"])
            for c in coms
            if MARCA_CI in c["body"] or MARCA_CONFLITO in c["body"]
        ]
        if cobrancas:
            ultima = max(cobrancas)
            if ultimo_commit < ultima and agora() - ultima > timedelta(
                hours=SEM_REACAO_HORAS
            ):
                fechar(
                    pr,
                    f"nenhum commit novo {SEM_REACAO_HORAS} h depois da cobrança do guardião.",
                )
                continue

        # 3. Conflitos
        conflito = medir_conflito(pr["headRefName"])
        if conflito is None:
            continue
        arquivos, linhas, acrescimo = conflito
        lista = "\n".join(f"- `{a}`" for a in arquivos)
        if acrescimo:
            lista += (
                f"\n\nAlém disso, {acrescimo} linhas são só acréscimo dos dois lados "
                "(a base do trecho está vazia): mantenha os dois blocos, sem escolher um."
            )
        if len(arquivos) > CONFLITO_MAX_ARQUIVOS or linhas > CONFLITO_MAX_LINHAS:
            fechar(
                pr,
                f"conflito grande com a `main` ({len(arquivos)} arquivos, {linhas} linhas).",
                lista,
            )
            continue
        ja_pediu = any(
            MARCA_CONFLITO in c["body"] and data(c["createdAt"]) > ultimo_commit
            for c in coms
        )
        if not ja_pediu:
            comentar(
                pr["number"],
                f"{MARCA_CONFLITO}\n@jules este PR tem conflito pequeno com a `main` "
                f"({len(arquivos)} arquivos, {linhas} linhas). Traga a `main` para esta "
                "branch (`git fetch origin && git merge origin/main`), resolva, rode os "
                f"testes e dê push **nesta mesma branch**.\n\n{lista}\n\n"
                f"{retomada(pr['headRefName'])}\n\n"
                f"Se não houver commit novo em {SEM_REACAO_HORAS} h, este PR será fechado.",
            )

    # 4. Branches órfãs: só as que já tiveram PR do agente, hoje fechado.
    # Branch de pessoa, com ou sem PR, fica (ADR 024).
    abertas = {
        p["headRefName"]
        for p in gh_json("pr", "list", "--state", "open", "--json", "headRefName")
    }
    do_jules = {
        p["headRefName"]
        for p in gh_json(
            "pr",
            "list",
            "--state",
            "closed",
            "--json",
            "headRefName,author",
            "--limit",
            "200",
        )
        if do_agente((p.get("author") or {}).get("login"))
    }
    sh("git", "fetch", "-q", "--prune", "origin")
    saida = sh(
        "git",
        "for-each-ref",
        "--format=%(refname:lstrip=3) %(committerdate:iso8601-strict)",
        "refs/remotes/origin",
    )
    for linha in saida.splitlines():
        nome, _, quando = linha.partition(" ")
        if nome in {"HEAD", "main"} or nome in abertas or not quando:
            continue
        if nome not in do_jules:
            continue
        if agora() - data(quando) > timedelta(hours=ORFA_HORAS):
            sh("git", "push", "-q", "origin", "--delete", nome, check=False)
            print(f"Branch órfã removida: {nome}")


def specs_ja_mudadas_na_main(branch: str, main: str = "origin/main") -> list[str]:
    """Specs que o PR altera e que a main alterou depois que a branch saiu dela.

    Duas sessões que dividem a mesma spec fazem a mesma troca para `draft`;
    edições idênticas não geram conflito, o CI passa nas duas e as duas eram
    mescladas (092a em 119a/b e 120a/b, #542 e #543). Se a main já mexeu na
    spec, o PR foi feito sobre uma versão velha dela e é redundante (ADR 024).
    """
    pasta = documentos()["specs"].rstrip("/") + "/"
    base = sh("git", "merge-base", main, f"origin/{branch}").strip()
    do_pr = sh("git", "diff", "--name-only", base, f"origin/{branch}").split()
    na_main = set(sh("git", "diff", "--name-only", base, main).split())
    return sorted(
        a for a in do_pr if a.startswith(pasta) and a.endswith(".md") and a in na_main
    )


REDUNDANTE = 10


def antes_do_merge(branch: str) -> int:
    """0 = pode mesclar; REDUNDANTE = o PR foi fechado como redundante.

    Qualquer outro código (um erro aqui) não impede o merge.
    """
    pr = next((p for p in prs_do_agente() if p["headRefName"] == branch), None)
    if pr is None:
        return 0
    sh("git", "fetch", "-q", "origin", "main", branch)
    mudadas = specs_ja_mudadas_na_main(branch)
    if not mudadas:
        return 0
    comentar(
        pr["number"],
        "Fechando sem merge: a `main` alterou estas specs depois que esta branch "
        "saiu dela, então o PR foi feito sobre uma versão velha e repetiria ou "
        "desfaria o que já entrou: "
        + ", ".join(f"`{a}`" for a in mudadas)
        + ". A raia recomeça da `main` atualizada na próxima rodada (ADR 024).",
    )
    sh("gh", "pr", "close", str(pr["number"]), "--delete-branch", check=False)
    print(f"PR #{pr['number']} fechado como redundante: {', '.join(mudadas)}")
    return REDUNDANTE


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ci-falhou", metavar="BRANCH")
    parser.add_argument("--run-id")
    parser.add_argument("--varredura", action="store_true")
    parser.add_argument("--antes-do-merge", metavar="BRANCH")
    args = parser.parse_args()
    if args.antes_do_merge:
        raise SystemExit(antes_do_merge(args.antes_do_merge))
    if args.ci_falhou:
        ci_falhou(args.ci_falhou, args.run_id or "")
    if args.varredura:
        varredura()


if __name__ == "__main__":
    main()
