"""Guardião de PRs: impede que PRs do agente fiquem travados.

Roda no GitHub Actions (workflow pr-guardiao.yml) com o gh CLI autenticado:
    python -m devagent.guardiao_prs ...

Modos:
    --ci-falhou BRANCH --run-id ID   CI falhou num PR: cobra o Jules ou fecha o PR
    --varredura                      conflitos, PRs sem reação, substituídos, branches órfãs

Regras (mantenha em sincronia com devagent/skills/destravar-pr.md):
    - CI falhou: comenta @jules com o log, até MAX_TENTATIVAS. Depois fecha o PR.
    - Falha irrecuperável: PR vazio ou só com registros de execução não tem
      nada a corrigir na branch (a sessão perdeu o trabalho). Fecha na hora,
      sem cobrar o agente, e abre `tentativa-falhou` (ADR 018). Cobrar só
      gerava sessões filhas com PRs vazios (#402 e #403, em 22/10).
    - Sem reação: se o guardião cobrou e não houve commit novo em SEM_REACAO_HORAS, fecha.
    - Conflito pequeno (<= CONFLITO_MAX_ARQUIVOS e <= CONFLITO_MAX_LINHAS): pede ao Jules
      para resolver. Conflito grande: fecha o PR; o próximo ciclo refaz a partir da main.
    - PR cujo corpo diz "Substitui #N": fecha o #N.
    - Issue citada com Closes/Fixes/Resolves num PR mergeado nos últimos 7 dias: fecha.
    - Ao fechar, abre issue `tentativa-falhou` com o motivo, para o próximo ciclo aprender.
      Exceção: se tudo o que o PR muda já chegou à main (sobram só registros de
      execução), fecha como absorvido e não abre issue (ADR 014).
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

from devagent.conferir_pr import FECHA_ISSUE, PADRAO_REGISTROS
from devagent.config import VERIFICACAO

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
    campos = "number,title,headRefName,headRefOid,body,labels,createdAt,url"
    prs = gh_json("pr", "list", "--state", "open", "--json", campos, "--limit", "50")
    return [p for p in prs if not p["title"].startswith("auditoria:")]


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
    corpo_issue = (
        f"O guardião fechou {pr['url']} ({pr['title']}).\n\n"
        f"**Motivo:** {motivo}\n\n"
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
    irrecuperavel = motivo_irrecuperavel(
        arquivos_do_pr(pr["number"]), pr.get("body") or ""
    )
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


def varredura() -> None:
    # Um passo auxiliar com defeito não pode cegar os outros: de 28/09 a 30/09
    # uma falha aqui derrubou a varredura inteira em toda execução.
    try:
        fechar_issues_citadas()
    except Exception as erro:  # noqa: BLE001
        print(f"::warning::fechar_issues_citadas falhou: {erro}")
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
        irrecuperavel = motivo_irrecuperavel(
            arquivos_do_pr(pr["number"]), pr.get("body") or ""
        )
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

    # 4. Branches órfãs (sem PR aberto e antigas)
    abertas = {
        p["headRefName"]
        for p in gh_json("pr", "list", "--state", "open", "--json", "headRefName")
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
        if agora() - data(quando) > timedelta(hours=ORFA_HORAS):
            sh("git", "push", "-q", "origin", "--delete", nome, check=False)
            print(f"Branch órfã removida: {nome}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ci-falhou", metavar="BRANCH")
    parser.add_argument("--run-id")
    parser.add_argument("--varredura", action="store_true")
    args = parser.parse_args()
    if args.ci_falhou:
        ci_falhou(args.ci_falhou, args.run_id or "")
    if args.varredura:
        varredura()


if __name__ == "__main__":
    main()
