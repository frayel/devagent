"""Dispara e destrava sessões do Jules pela API, sem depender da interface web.

Por que existe: tarefas criadas pela interface do Jules podem parar em
"aguardando aprovação do plano" quando o Planning Critic decide que o plano
precisa de revisão humana. O texto do prompt não muda isso. Pela API, uma
sessão criada sem `requirePlanApproval` tem o plano aprovado automaticamente,
e sessões que mesmo assim pararem são destravadas aqui.

Uso:
    python scripts/jules.py iniciar desenvolvedor
    python scripts/jules.py iniciar auditor
    python scripts/jules.py destravar          # aprova planos e responde perguntas
    python scripts/jules.py listar
    python scripts/jules.py iniciar auditor --dry-run

Variáveis de ambiente:
    JULES_API_KEY   chave criada em https://jules.google.com/settings#api
    JULES_SOURCE    opcional; padrão sources/github/frayel/devagent

Só usa a biblioteca padrão.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any

API = "https://jules.googleapis.com/v1alpha"
SOURCE = os.environ.get("JULES_SOURCE", "sources/github/frayel/devagent")
ATIVOS = {
    "QUEUED",
    "PLANNING",
    "AWAITING_PLAN_APPROVAL",
    "AWAITING_USER_FEEDBACK",
    "IN_PROGRESS",
    "PAUSED",
}

PERSONAS = {
    "desenvolvedor": {
        "titulo": "Desenvolvedor · ciclo",
        "prompt": (
            "Você é o desenvolvedor autônomo deste repositório. Execute uma "
            "iteração do ciclo de decisão do AGENTS.md: leia o estado, escolha "
            "o primeiro passo aplicável, entregue um PR e o relatório em "
            "docs/runs/. Não peça aprovação de plano e não faça perguntas: diante "
            "de ambiguidade, escolha a opção mais conservadora, registre a "
            "decisão no relatório e siga."
        ),
    },
    "auditor": {
        "titulo": "Auditor · produção",
        "prompt": (
            "Você é o Auditor de Produção do Painel B3, não o desenvolvedor. "
            "Leia e siga docs/agents/auditor.md do começo ao fim. Ignore o ciclo "
            "de decisão do AGENTS.md; dele valem só as seções 2, 9 e 10. Não "
            "altere app/, tests/, docs/specs/ nem AGENTS.md. Entregue um único "
            'PR com título "auditoria: AAAA-MM-DD · N achados", contendo só '
            "arquivos de docs/auditoria/. Não peça aprovação e não faça perguntas."
        ),
    },
}

RESPOSTA_PADRAO = (
    "Não há humano acompanhando esta sessão. Não espere respostas nem "
    "aprovação. Escolha a opção mais conservadora, registre a decisão no "
    "relatório ou no corpo do PR e continue até abrir o PR."
)


def chamar(metodo: str, caminho: str, corpo: dict[str, Any] | None = None) -> Any:
    chave = os.environ.get("JULES_API_KEY")
    if not chave:
        print("JULES_API_KEY ausente", file=sys.stderr)
        sys.exit(3)
    dados = json.dumps(corpo).encode() if corpo is not None else None
    req = urllib.request.Request(
        f"{API}/{caminho}",
        data=dados,
        method=metodo,
        headers={"x-goog-api-key": chave, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            texto = resp.read().decode()
    except urllib.error.HTTPError as e:
        print(f"{metodo} {caminho}: HTTP {e.code} {e.read().decode()}", file=sys.stderr)
        raise
    return json.loads(texto) if texto.strip() else {}


def sessoes_do_repo(paginas: int = 3) -> list[dict[str, Any]]:
    todas: list[dict[str, Any]] = []
    token = ""
    for _ in range(paginas):
        caminho = "sessions?pageSize=100" + (f"&pageToken={token}" if token else "")
        resp = chamar("GET", caminho)
        todas += resp.get("sessions", [])
        token = resp.get("nextPageToken", "")
        if not token:
            break
    return [s for s in todas if (s.get("sourceContext") or {}).get("source") == SOURCE]


def _data(s: dict[str, Any], campo: str) -> datetime:
    valor = s.get(campo) or s.get("createTime") or "1970-01-01T00:00:00Z"
    return datetime.fromisoformat(valor.replace("Z", "+00:00"))


def iniciar(persona: str, dry_run: bool) -> int:
    p = PERSONAS[persona]
    corpo = {
        "title": p["titulo"],
        "prompt": p["prompt"],
        "sourceContext": {
            "source": SOURCE,
            "githubRepoContext": {"startingBranch": "main"},
        },
        "automationMode": "AUTO_CREATE_PR",
        "requirePlanApproval": False,
    }
    if dry_run:
        print(json.dumps(corpo, ensure_ascii=False, indent=2))
        return 0
    for s in sessoes_do_repo():
        if s.get("title", "").startswith(p["titulo"]) and s.get("state") in ATIVOS:
            print(f"Já existe sessão ativa de {persona}: {s['name']} ({s['state']})")
            return 0
    nova = chamar("POST", "sessions", corpo)
    print(f"Sessão criada: {nova.get('name')} {nova.get('url', '')}")
    return 0


def destravar(espera_minutos: int) -> int:
    agora = datetime.now(timezone.utc)
    for s in sessoes_do_repo():
        estado = s.get("state")
        nome = s["name"]
        if estado == "AWAITING_PLAN_APPROVAL":
            chamar("POST", f"{nome}:approvePlan", {})
            print(f"Plano aprovado: {nome} ({s.get('title', '')})")
        elif estado == "AWAITING_USER_FEEDBACK":
            # Responde só se a sessão está parada há algum tempo, para não
            # atropelar uma pergunta que acabou de ser feita e já será retomada.
            if agora - _data(s, "updateTime") >= timedelta(minutes=espera_minutos):
                chamar("POST", f"{nome}:sendMessage", {"prompt": RESPOSTA_PADRAO})
                print(f"Pergunta respondida: {nome} ({s.get('title', '')})")
    return 0


def listar() -> int:
    for s in sessoes_do_repo():
        print(
            f"{s.get('state', '?'):24} {s.get('createTime', '')[:16]} {s.get('title', '')}"
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("iniciar")
    i.add_argument("persona", choices=sorted(PERSONAS))
    i.add_argument("--dry-run", action="store_true")
    d = sub.add_parser("destravar")
    d.add_argument("--espera-minutos", type=int, default=10)
    sub.add_parser("listar")
    args = ap.parse_args(argv)
    if args.cmd == "iniciar":
        return iniciar(args.persona, args.dry_run)
    if args.cmd == "destravar":
        return destravar(args.espera_minutos)
    return listar()


if __name__ == "__main__":
    sys.exit(main())
