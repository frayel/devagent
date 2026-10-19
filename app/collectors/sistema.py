"""Estado do fluxo de desenvolvimento e do deploy, para a página /sistema (spec 082).

Lê o GitHub (workflows, PRs, issues, commits), a API do Jules e a API do
Render num laço em segundo plano e guarda o resultado em memória. A página só
lê esse retrato: visita nenhuma dispara requisição (PRODUTO.md, seção 5).

Variáveis de ambiente, todas opcionais:
    GITHUB_TOKEN        token só de leitura; sem ele o GitHub limita a 60
                        consultas por hora e o retrato é refeito a cada 20 min
    JULES_API_KEY       liga a leitura das sessões do Jules
    JULES_LIMITE_DIARIO teto de sessões em 24 h do plano do Jules
    RENDER_API_KEY      liga a leitura do último deploy no Render
    RENDER_SERVICE_ID   id do serviço; o Render já define esta variável
    RENDER_GIT_COMMIT   commit em produção; o Render já define esta variável
    MONITOR_SISTEMA     0 desliga o laço
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import subprocess
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from app.collectors.utils import USER_AGENT, _enforce_rate_limit

logger = logging.getLogger(__name__)

RAIZ = Path(__file__).resolve().parent.parent.parent
GITHUB = "https://api.github.com"
JULES = "https://jules.googleapis.com/v1alpha"
RENDER = "https://api.render.com/v1"
TIMEOUT = 10.0
INTERVALO_COM_TOKEN = 5 * 60
INTERVALO_SEM_TOKEN = 20 * 60

CRON = re.compile(r"""^\s*-\s*cron:\s*["']([^"']+)["']""", re.MULTILINE)
NOME = re.compile(r"""^name:\s*["']?(.+?)["']?\s*$""", re.MULTILINE)

# Último retrato. Cada parte é None até a primeira leitura bem-sucedida; o
# erro da parte fica em <parte>_erro.
retrato: dict[str, Any] = {
    "atualizado_em": None,
    "github": None,
    "github_erro": None,
    "jules": None,
    "jules_erro": None,
    "render": None,
    "render_erro": None,
}


class SemRepositorio(Exception):
    pass


def monitor_ligado() -> bool:
    if "PYTEST_CURRENT_TEST" in os.environ:
        return False
    return os.environ.get("MONITOR_SISTEMA", "1") not in {"0", "false", "False"}


def repositorio() -> str:
    """owner/nome do repositório, de devagent.toml (GITHUB_REPOSITORY tem precedência)."""
    do_ambiente = os.environ.get("GITHUB_REPOSITORY", "").strip()
    if do_ambiente:
        return do_ambiente
    try:
        with open(RAIZ / "devagent.toml", "rb") as f:
            return str(tomllib.load(f)["projeto"]["repositorio"])
    except (OSError, KeyError, tomllib.TOMLDecodeError) as e:
        raise SemRepositorio("repositório não encontrado em devagent.toml") from e


def commit_em_producao() -> str | None:
    """O Render define RENDER_GIT_COMMIT; fora dele, o HEAD do checkout local."""
    sha = os.environ.get("RENDER_GIT_COMMIT", "").strip()
    if sha:
        return sha
    try:
        saida = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=RAIZ,
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return saida.stdout.strip() or None


def workflows_do_repositorio(raiz: Path = RAIZ) -> list[dict[str, Any]]:
    """Workflows versionados: arquivo, nome e agendamentos cron."""
    saida = []
    for arquivo in sorted((raiz / ".github" / "workflows").glob("*.y*ml")):
        texto = arquivo.read_text(encoding="utf-8")
        nome = NOME.search(texto)
        saida.append(
            {
                "arquivo": arquivo.name,
                "caminho": f".github/workflows/{arquivo.name}",
                "nome": nome.group(1) if nome else arquivo.stem,
                "crons": CRON.findall(texto),
            }
        )
    return saida


# --------------------------------------------------------------------------
# GitHub
# --------------------------------------------------------------------------


def _get_github(client: httpx.Client, caminho: str) -> Any:
    _enforce_rate_limit("api.github.com")
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": USER_AGENT,
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    resposta = client.get(f"{GITHUB}{caminho}", headers=headers, timeout=TIMEOUT)
    restante = resposta.headers.get("x-ratelimit-remaining")
    if restante is not None:
        _limite["restante"] = int(restante)
        _limite["total"] = int(resposta.headers.get("x-ratelimit-limit", "0"))
    if resposta.status_code in (403, 429) and restante == "0":
        raise RuntimeError("limite da API do GitHub esgotado")
    resposta.raise_for_status()
    return resposta.json()


_limite: dict[str, int] = {}


def _primeira_linha(texto: str | None) -> str:
    linhas = (texto or "").strip().splitlines()
    return linhas[0] if linhas else ""


def _run(r: dict[str, Any]) -> dict[str, Any]:
    return {
        "nome": r.get("name"),
        "caminho": r.get("path", "").split("@")[0],
        "evento": r.get("event"),
        "status": r.get("status"),
        "conclusao": r.get("conclusion"),
        "criado_em": r.get("created_at"),
        "url": r.get("html_url"),
        "branch": r.get("head_branch"),
    }


def ler_github(client: httpx.Client) -> dict[str, Any]:
    repo = repositorio()
    workflows = workflows_do_repositorio()
    runs = [
        _run(r)
        for r in _get_github(client, f"/repos/{repo}/actions/runs?per_page=100")[
            "workflow_runs"
        ]
    ]
    vistos = {r["caminho"] for r in runs}

    ultimo_agendado: dict[str, dict[str, Any] | None] = {}
    for wf in workflows:
        base = f"/repos/{repo}/actions/workflows/{wf['arquivo']}/runs?per_page=1"
        if wf["caminho"] not in vistos:
            achados = _get_github(client, base)["workflow_runs"]
            runs += [_run(r) for r in achados]
        if wf["crons"]:
            achados = _get_github(client, base + "&event=schedule")["workflow_runs"]
            ultimo_agendado[wf["caminho"]] = _run(achados[0]) if achados else None

    prs = [
        {
            "numero": p["number"],
            "titulo": p["title"],
            "criado_em": p["created_at"],
            "url": p["html_url"],
            "autor": (p.get("user") or {}).get("login"),
            "rascunho": p.get("draft", False),
        }
        for p in _get_github(client, f"/repos/{repo}/pulls?state=open&per_page=50")
    ]
    issues = [
        {
            "numero": i["number"],
            "titulo": i["title"],
            "criado_em": i["created_at"],
            "url": i["html_url"],
            "labels": [lb["name"] for lb in i.get("labels", [])],
        }
        for i in _get_github(client, f"/repos/{repo}/issues?state=open&per_page=100")
        if "pull_request" not in i
    ]
    head = _get_github(client, f"/repos/{repo}/commits/main")
    main = {
        "sha": head["sha"],
        "data": head["commit"]["committer"]["date"],
        "mensagem": _primeira_linha(head["commit"]["message"]),
        "url": head.get("html_url"),
    }

    producao: dict[str, Any] | None = None
    sha = commit_em_producao()
    if sha:
        if sha == main["sha"]:
            producao = {**main, "atras": 0}
        else:
            comp = _get_github(client, f"/repos/{repo}/compare/{sha}...main")
            base_commit = comp.get("base_commit") or {}
            dados = base_commit.get("commit") or {}
            producao = {
                "sha": sha,
                "data": (dados.get("committer") or {}).get("date"),
                "mensagem": _primeira_linha(dados.get("message")),
                "url": base_commit.get("html_url"),
                "atras": int(comp.get("ahead_by", 0)),
            }

    return {
        "repositorio": repo,
        "workflows": workflows,
        "runs": runs,
        "ultimo_agendado": ultimo_agendado,
        "prs": prs,
        "issues": issues,
        "main": main,
        "producao": producao,
        "limite": dict(_limite),
        "com_token": bool(os.environ.get("GITHUB_TOKEN", "").strip()),
    }


# --------------------------------------------------------------------------
# Jules e Render
# --------------------------------------------------------------------------


def ler_jules(client: httpx.Client) -> dict[str, Any] | None:
    chave = os.environ.get("JULES_API_KEY", "").strip()
    if not chave:
        return None
    _enforce_rate_limit("jules.googleapis.com")
    resposta = client.get(
        f"{JULES}/sessions?pageSize=100",
        headers={"x-goog-api-key": chave, "User-Agent": USER_AGENT},
        timeout=TIMEOUT,
    )
    resposta.raise_for_status()
    fonte = f"sources/github/{repositorio()}"
    sessoes = [
        {
            "titulo": s.get("title", ""),
            "estado": s.get("state", ""),
            "criada_em": s.get("createTime"),
            "atualizada_em": s.get("updateTime") or s.get("createTime"),
            "url": s.get("url"),
        }
        for s in resposta.json().get("sessions", [])
        if (s.get("sourceContext") or {}).get("source") == fonte
    ]
    return {"sessoes": sessoes}


def ler_render(client: httpx.Client) -> dict[str, Any] | None:
    chave = os.environ.get("RENDER_API_KEY", "").strip()
    servico = os.environ.get("RENDER_SERVICE_ID", "").strip()
    if not (chave and servico):
        return None
    _enforce_rate_limit("api.render.com")
    resposta = client.get(
        f"{RENDER}/services/{servico}/deploys?limit=1",
        headers={"Authorization": f"Bearer {chave}", "Accept": "application/json"},
        timeout=TIMEOUT,
    )
    resposta.raise_for_status()
    itens = resposta.json()
    if not itens:
        return {"deploy": None}
    d = itens[0].get("deploy", itens[0])
    commit = d.get("commit") or {}
    return {
        "deploy": {
            "status": d.get("status"),
            "criado_em": d.get("createdAt"),
            "terminado_em": d.get("finishedAt"),
            "sha": commit.get("id"),
            "mensagem": _primeira_linha(commit.get("message")),
        }
    }


# --------------------------------------------------------------------------
# Laço
# --------------------------------------------------------------------------


def _erro(e: Exception) -> str:
    if isinstance(e, httpx.HTTPStatusError):
        return f"HTTP {e.response.status_code}"
    return str(e)[:200] or type(e).__name__


def atualizar(client: httpx.Client | None = None) -> None:
    """Refaz o retrato. Falha de uma parte não apaga o retrato anterior dela."""
    proprio = client is None
    client = client or httpx.Client()
    try:
        for parte, leitor in (
            ("github", ler_github),
            ("jules", ler_jules),
            ("render", ler_render),
        ):
            try:
                retrato[parte] = leitor(client)
                retrato[f"{parte}_erro"] = None
            except Exception as e:  # noqa: BLE001 - a página mostra o erro
                logger.warning("Monitor do sistema: %s falhou (%s)", parte, _erro(e))
                retrato[f"{parte}_erro"] = _erro(e)
        retrato["atualizado_em"] = datetime.now(timezone.utc).isoformat()
    finally:
        if proprio:
            client.close()


def intervalo() -> int:
    if os.environ.get("GITHUB_TOKEN", "").strip():
        return INTERVALO_COM_TOKEN
    return INTERVALO_SEM_TOKEN


async def laco_do_monitor() -> None:
    while True:
        await asyncio.to_thread(atualizar)
        await asyncio.sleep(intervalo())
