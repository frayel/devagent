"""Mostra o estado do repositório no GitHub: PRs abertos, CI, conflitos e issues.

Primeiro comando de toda execução do agente (devagent/CICLO.md).

Uso:
    python -m devagent.estado_github          # texto legível
    python -m devagent.estado_github --json   # para scripts

Funciona sem autenticação em repositório público (limite de 60 req/h).
Se GITHUB_TOKEN ou GH_TOKEN estiver no ambiente, usa o token.
Só usa a biblioteca padrão.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any

from devagent import saude
from devagent.fila_specs import (
    LABELS_DE_PRODUCAO,
    correcao_mergeada,
    fila_da_revisao,
    instrucao,
    producao_pendente,
    specs_prontas,
)
from devagent.raias import AUDITORIA, DESENVOLVIMENTO, do_agente, raia_do_titulo

API = "https://api.github.com"


def _repo() -> str:
    env = os.environ.get("GITHUB_REPOSITORY")
    if env:
        return env
    url = subprocess.run(
        ["git", "remote", "get-url", "origin"], capture_output=True, text=True
    ).stdout.strip()
    m = re.search(r"github\.com[:/](.+?/.+?)(?:\.git)?$", url)
    if not m:
        sys.exit("Não consegui descobrir o repositório (defina GITHUB_REPOSITORY).")
    return m.group(1)


def _get(path: str) -> Any:
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(f"{API}{path}", headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def marcar_correcoes(repo: str, issues: list[dict[str, Any]]) -> None:
    """Marca `correcao_mergeada` nas issues de produção, lendo os comentários.

    É o código, não o agente, que decide se a issue espera só a verificação
    (ADR 026). Sem acesso aos comentários, a issue fica pendente.
    """
    for i in issues:
        if not set(i.get("labels", [])) & set(LABELS_DE_PRODUCAO):
            continue
        try:
            comentarios = _get(
                f"/repos/{repo}/issues/{i['numero']}/comments?per_page=100"
            )
        except (urllib.error.URLError, OSError, ValueError):
            i["correcao_mergeada"] = False
            continue
        i["correcao_mergeada"] = correcao_mergeada(
            [c.get("body") or "" for c in comentarios]
        )


def _horas(iso: str) -> float:
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return round((datetime.now(timezone.utc) - dt).total_seconds() / 3600, 1)


def eh_do_agente(pr: dict[str, Any]) -> bool:
    """PR da raia de desenvolvimento: o que trava a próxima sessão dela.

    PRs das raias auxiliares (spec, revisão, verificação) e do auditor correm
    em paralelo e não contam na regra de um PR aberto por vez (ADR 021). PR
    de outro autor, como o dono do produto, também não: o agente não mexe
    nele (ADR 024).
    """
    autor = (pr.get("user") or {}).get("login")
    return do_agente(autor) and raia_do_titulo(pr["title"]) == DESENVOLVIMENTO


def status_ci(repo: str, sha: str) -> str:
    runs = _get(f"/repos/{repo}/commits/{sha}/check-runs?per_page=100")["check_runs"]
    if not runs:
        return "sem_ci"
    if any(r["status"] != "completed" for r in runs):
        return "rodando"
    ruins = {"failure", "timed_out", "cancelled", "action_required"}
    if any(r["conclusion"] in ruins for r in runs):
        falhos = sorted({r["name"] for r in runs if r["conclusion"] in ruins})
        return "falhou: " + ", ".join(falhos)
    return "passou"


def coletar() -> dict[str, Any]:
    repo = _repo()
    prs = []
    for pr in _get(f"/repos/{repo}/pulls?state=open&per_page=50"):
        detalhe = _get(f"/repos/{repo}/pulls/{pr['number']}")
        prs.append(
            {
                "numero": pr["number"],
                "titulo": pr["title"],
                "branch": pr["head"]["ref"],
                "do_agente": eh_do_agente(pr),
                "humano": not do_agente((pr.get("user") or {}).get("login")),
                "raia": raia_do_titulo(pr["title"]),
                "labels": [lbl["name"] for lbl in pr["labels"]],
                "idade_horas": _horas(pr["created_at"]),
                "ci": status_ci(repo, pr["head"]["sha"]),
                # mergeable_state: clean, dirty (conflito), blocked, unstable, unknown
                "merge": detalhe.get("mergeable_state", "unknown"),
                "comentarios": detalhe.get("comments", 0)
                + detalhe.get("review_comments", 0),
            }
        )
    issues = [
        {
            "numero": i["number"],
            "titulo": i["title"],
            "labels": [lbl["name"] for lbl in i["labels"]],
            "idade_horas": _horas(i["created_at"]),
            "corpo": i.get("body") or "",
        }
        for i in _get(f"/repos/{repo}/issues?state=open&per_page=100")
        if "pull_request" not in i
    ]
    marcar_correcoes(repo, issues)
    return {"repo": repo, "prs": prs, "issues": issues}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        estado = coletar()
    except urllib.error.URLError as exc:
        print(f"Falha ao consultar o GitHub: {exc}", file=sys.stderr)
        return 3

    if args.json:
        for i in estado["issues"]:
            i.pop("corpo", None)
        print(json.dumps(estado, ensure_ascii=False, indent=2))
        return 0

    print(f"Repositório: {estado['repo']}\n")
    agente = [p for p in estado["prs"] if p["do_agente"]]
    print(f"PRs abertos do agente (raia de desenvolvimento): {len(agente)}")
    for p in agente:
        print(
            f"  #{p['numero']} [{p['branch']}] {p['titulo']}\n"
            f"      CI: {p['ci']} · merge: {p['merge']} · "
            f"{p['idade_horas']} h · comentários: {p['comentarios']}"
        )
    raias = [
        p
        for p in estado["prs"]
        if not p["do_agente"] and not p["humano"] and p["raia"] != AUDITORIA
    ]
    if raias:
        print(
            f"\nPRs das raias paralelas (spec, revisão, verificação): {len(raias)}. "
            "Só a sessão da raia mexe no PR dela."
        )
        for p in raias:
            print(f"  #{p['numero']} [{p['raia']}] {p['titulo']} · CI: {p['ci']}")
    humanos = [p for p in estado["prs"] if p["humano"]]
    if humanos:
        print(f"\nPRs de pessoas (não são do agente; não mexa neles): {len(humanos)}")
        for p in humanos:
            print(f"  #{p['numero']} {p['titulo']}")
    outros = [p for p in estado["prs"] if p["raia"] == AUDITORIA and not p["humano"]]
    if outros:
        print(f"\nPRs do auditor (ignore): {len(outros)}")
        for p in outros:
            print(f"  #{p['numero']} {p['titulo']} {p['labels']}")
    print(f"\nIssues abertas: {len(estado['issues'])}")
    for i in estado["issues"]:
        print(f"  #{i['numero']} {i['labels']} {i['titulo']}")

    # Cadências do Passo 7, calculadas das specs (ADR 024).
    try:
        from devagent.cadencias import calcular, resumo

        print("\n" + resumo(calcular()))
    except OSError:
        pass

    # Saúde de produção (ADR 016): o que a página do produto acusa agora.
    problemas_em_producao = False
    try:
        dados = saude.ler(espera=90)
    except saude.Indisponivel as exc:
        print(f"\nSaúde de produção indisponível: {exc}")
    else:
        print("\n" + saude.resumo(dados))
        problemas_em_producao = bool(saude.pendentes(dados, "problema"))

    prontas = specs_prontas()
    em_revisao = {p.name for p in fila_da_revisao(prontas)}
    print(f"\nSpecs ready na fila: {len(prontas)}")
    for p in prontas[:5]:
        marca = " (esperando revisão)" if p.name in em_revisao else ""
        print(f"  {p.name}{marca}")

    bloqueada = next(
        (
            i
            for i in estado["issues"]
            if saude.LABEL in i["labels"] and "bloqueado" in i["labels"]
        ),
        None,
    )
    if problemas_em_producao and bloqueada:
        print(
            f"\n>> Os problemas de produção já estão na issue #{bloqueada['numero']}, "
            "bloqueada à espera de ação humana. Não insista neles; siga o ciclo."
        )
    elif problemas_em_producao:
        print(
            "\n>> A produção acusa problema: o Passo 1 vem antes de tudo. Corrija o "
            f"que tem causa no repositório; o que depende de configuração externa "
            f"vai descrito na issue `{saude.LABEL}` com o label `bloqueado`."
        )
    if agente:
        print(
            "\n>> Existe PR do agente aberto: siga o Passo 2 (destravar o PR). "
            "Não comece trabalho novo."
        )
    elif prontas or producao_pendente(estado["issues"]):
        print(f"\n>> {instrucao(prontas, issues=estado['issues'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
