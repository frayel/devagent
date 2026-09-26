"""Consulta o status do último deploy no Render e, se falhou, traz os logs.

Uso:
    python scripts/render_status.py            # consulta uma vez
    python scripts/render_status.py --wait 900 # espera até 900 s o deploy terminar
    python scripts/render_status.py --commit <sha>  # deploy de um commit específico

Variáveis de ambiente:
    RENDER_API_KEY     chave da API do Render (Account Settings > API Keys)
    RENDER_SERVICE_ID  id do web service (srv-...), visível na URL do dashboard

Saída: JSON em stdout. Código de saída:
    0 deploy live · 1 deploy falhou · 2 ainda em andamento · 3 configuração ausente ou erro de API

Só usa a biblioteca padrão, para rodar em qualquer ambiente sem instalar nada.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

API = "https://api.render.com/v1"
OK = {"live"}
FAILED = {"build_failed", "update_failed", "pre_deploy_failed", "canceled"}


def _get(path: str, params: dict[str, Any] | None = None) -> Any:
    url = f"{API}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params, doseq=True)
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {os.environ['RENDER_API_KEY']}",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def latest_deploy(service_id: str, commit: str | None) -> dict[str, Any] | None:
    items = _get(f"/services/{service_id}/deploys", {"limit": 20})
    for item in items:
        deploy = item.get("deploy", item)
        sha = (deploy.get("commit") or {}).get("id", "")
        if commit is None or sha.startswith(commit) or commit.startswith(sha or "-"):
            return deploy
    return None


def fetch_logs(service_id: str, deploy: dict[str, Any]) -> list[str]:
    service = _get(f"/services/{service_id}")
    owner_id = service.get("ownerId") or service.get("service", {}).get("ownerId")
    params: dict[str, Any] = {
        "ownerId": owner_id,
        "resource": [service_id],
        "limit": 100,
        "direction": "backward",
    }
    if deploy.get("createdAt"):
        params["startTime"] = deploy["createdAt"]
    data = _get("/logs", params)
    logs = data.get("logs", [])
    lines = [f"{log.get('timestamp', '')} {log.get('message', '')}" for log in logs]
    return list(reversed(lines))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wait", type=int, default=0, help="segundos de espera")
    parser.add_argument("--commit", default=None, help="sha do commit esperado")
    args = parser.parse_args()

    service_id = os.environ.get("RENDER_SERVICE_ID")
    if not os.environ.get("RENDER_API_KEY") or not service_id:
        print(json.dumps({"erro": "RENDER_API_KEY ou RENDER_SERVICE_ID ausente"}))
        return 3

    deadline = time.time() + args.wait
    try:
        while True:
            deploy = latest_deploy(service_id, args.commit)
            status = deploy.get("status") if deploy else "nao_encontrado"
            if status in OK or status in FAILED or time.time() >= deadline:
                break
            time.sleep(20)

        result: dict[str, Any] = {
            "status": status,
            "deploy_id": deploy.get("id") if deploy else None,
            "commit": ((deploy or {}).get("commit") or {}).get("id"),
            "finished_at": (deploy or {}).get("finishedAt"),
        }
        if deploy and status in FAILED:
            result["logs"] = fetch_logs(service_id, deploy)
    except (urllib.error.URLError, KeyError, ValueError) as exc:
        print(json.dumps({"erro": f"falha ao consultar a API do Render: {exc}"}))
        return 3

    print(json.dumps(result, ensure_ascii=False, indent=2))
    if status in OK:
        return 0
    if status in FAILED:
        return 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
