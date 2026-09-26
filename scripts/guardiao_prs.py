"""Guardião de PRs: impede que PRs do agente fiquem travados.

Roda no GitHub Actions (workflow pr-guardiao.yml) com o gh CLI autenticado.

Modos:
    --ci-falhou BRANCH --run-id ID   CI falhou num PR: cobra o Jules ou fecha o PR
    --varredura                      conflitos, PRs sem reação, substituídos, branches órfãs

Regras (mantenha em sincronia com docs/skills/destravar-pr.md):
    - CI falhou: comenta @jules com o log, até MAX_TENTATIVAS. Depois fecha o PR.
    - Sem reação: se o guardião cobrou e não houve commit novo em SEM_REACAO_HORAS, fecha.
    - Conflito pequeno (<= CONFLITO_MAX_ARQUIVOS e <= CONFLITO_MAX_LINHAS): pede ao Jules
      para resolver. Conflito grande: fecha o PR; o próximo ciclo refaz a partir da main.
    - PR cujo corpo diz "Substitui #N": fecha o #N.
    - Ao fechar, abre issue `tentativa-falhou` com o motivo, para o próximo ciclo aprender.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import datetime, timedelta, timezone
from typing import Any

MAX_TENTATIVAS = 3
SEM_REACAO_HORAS = 3
CONFLITO_MAX_ARQUIVOS = 3
CONFLITO_MAX_LINHAS = 40
ORFA_HORAS = 24

MARCA_CI = "<!-- guardiao:ci -->"
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
    return [
        p
        for p in prs
        if not p["title"].startswith("auditoria:")
        and "revisao-humana" not in {lbl["name"] for lbl in p["labels"]}
    ]


def comentarios(numero: int) -> list[dict[str, Any]]:
    return gh_json("pr", "view", str(numero), "--json", "comments")["comments"]


def data_ultimo_commit(numero: int) -> datetime:
    commits = gh_json("pr", "view", str(numero), "--json", "commits")["commits"]
    return data(commits[-1]["committedDate"])


def comentar(numero: int, corpo: str) -> None:
    sh("gh", "pr", "comment", str(numero), "--body", corpo)


def fechar(pr: dict[str, Any], motivo: str, detalhe: str = "") -> None:
    numero = pr["number"]
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
    tentativas = sum(MARCA_CI in c["body"] for c in comentarios(pr["number"]))
    log = sh("gh", "run", "view", run_id, "--log-failed", check=False)
    log = "\n".join(log.splitlines()[-120:])
    if tentativas >= MAX_TENTATIVAS:
        fechar(pr, f"o CI falhou {tentativas + 1} vezes seguidas.", log)
        return
    comentar(
        pr["number"],
        f"{MARCA_CI}\n@jules o CI falhou neste PR (cobrança {tentativas + 1} de "
        f"{MAX_TENTATIVAS}). Corrija **nesta mesma branch**, sem abrir PR novo. "
        "Reproduza localmente com `ruff check . && ruff format --check . && mypy app "
        "&& pytest -q` e o smoke test descrito em `docs/skills/destravar-pr.md`.\n\n"
        f"Se não houver commit novo em {SEM_REACAO_HORAS} h, este PR será fechado.\n\n"
        f"<details><summary>Log da falha</summary>\n\n```\n{log}\n```\n</details>",
    )
    print(f"Cobrança {tentativas + 1} enviada ao PR #{pr['number']}")


def medir_conflito(branch: str) -> tuple[list[str], int] | None:
    """Faz um merge de teste da branch na main. None = sem conflito."""
    sh("git", "fetch", "-q", "origin", "main", branch)
    sh("git", "checkout", "-q", "--detach", "origin/main")
    r = subprocess.run(
        ["git", "merge", "--no-commit", "--no-ff", f"origin/{branch}"],
        capture_output=True,
        text=True,
    )
    try:
        if r.returncode == 0:
            return None
        arquivos = sh("git", "diff", "--name-only", "--diff-filter=U").split()
        linhas = 0
        for arq in arquivos:
            dentro = False
            try:
                with open(arq, encoding="utf-8", errors="replace") as f:
                    for linha in f:
                        if linha.startswith("<<<<<<<"):
                            dentro = True
                        elif linha.startswith(">>>>>>>"):
                            dentro = False
                        elif dentro and not linha.startswith("======="):
                            linhas += 1
            except OSError:
                linhas += (
                    CONFLITO_MAX_LINHAS + 1
                )  # arquivo removido/binário: conta como grande
        return arquivos, linhas
    finally:
        sh("git", "merge", "--abort", check=False)
        sh("git", "reset", "-q", "--hard", check=False)


def varredura() -> None:
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
        arquivos, linhas = conflito
        lista = "\n".join(f"- `{a}`" for a in arquivos)
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
