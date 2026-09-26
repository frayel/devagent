"""Mostra o estado do repositório no GitHub: PRs abertos, CI, conflitos e issues.

Primeiro comando de toda execução do agente (seção 5 do AGENTS.md).

Uso:
    python scripts/estado_github.py          # texto legível
    python scripts/estado_github.py --json   # para scripts

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


def _horas(iso: str) -> float:
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return round((datetime.now(timezone.utc) - dt).total_seconds() / 3600, 1)


def eh_do_agente(pr: dict[str, Any]) -> bool:
    labels = {lbl["name"] for lbl in pr.get("labels", [])}
    return not pr["title"].startswith("auditoria:") and "revisao-humana" not in labels


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
        }
        for i in _get(f"/repos/{repo}/issues?state=open&per_page=100")
        if "pull_request" not in i
    ]
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
        print(json.dumps(estado, ensure_ascii=False, indent=2))
        return 0

    print(f"Repositório: {estado['repo']}\n")
    agente = [p for p in estado["prs"] if p["do_agente"]]
    print(f"PRs abertos do agente: {len(agente)}")
    for p in agente:
        print(
            f"  #{p['numero']} [{p['branch']}] {p['titulo']}\n"
            f"      CI: {p['ci']} · merge: {p['merge']} · "
            f"{p['idade_horas']} h · comentários: {p['comentarios']}"
        )
    outros = [p for p in estado["prs"] if not p["do_agente"]]
    if outros:
        print(f"\nPRs que não são seus (ignore): {len(outros)}")
        for p in outros:
            print(f"  #{p['numero']} {p['titulo']} {p['labels']}")
    print(f"\nIssues abertas: {len(estado['issues'])}")
    for i in estado["issues"]:
        print(f"  #{i['numero']} {i['labels']} {i['titulo']}")

    if agente:
        print(
            "\n>> Existe PR do agente aberto: siga o Passo 2 (destravar o PR). "
            "Não comece trabalho novo."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
