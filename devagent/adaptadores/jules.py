"""Dispara e destrava sessões do Jules pela API, sem depender da interface web.

Por que existe: tarefas criadas pela interface do Jules podem parar em
"aguardando aprovação do plano" quando o Planning Critic decide que o plano
precisa de revisão humana. O texto do prompt não muda isso. Pela API, uma
sessão criada sem `requirePlanApproval` tem o plano aprovado automaticamente,
e sessões que mesmo assim pararem são destravadas aqui.

Uso:
    python -m devagent.adaptadores.jules iniciar desenvolvedor
    python -m devagent.adaptadores.jules iniciar auditor
    python -m devagent.adaptadores.jules iniciar seguranca | design | performance
    python -m devagent.adaptadores.jules destravar   # aprova planos e responde perguntas
    python -m devagent.adaptadores.jules listar
    python -m devagent.adaptadores.jules iniciar auditor --dry-run

Variáveis de ambiente:
    JULES_API_KEY   chave criada em https://jules.google.com/settings#api
    JULES_SOURCE    opcional; padrão sources/github/<repositorio do devagent.toml>

O nome do produto e o repositório vêm do devagent.toml; os prompts só apontam
para os arquivos do núcleo (devagent/CICLO.md e devagent/agents/).

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

from devagent.config import PROJETO

API = "https://jules.googleapis.com/v1alpha"
SOURCE = os.environ.get("JULES_SOURCE", f"sources/github/{PROJETO['repositorio']}")
PRODUTO = PROJETO["nome"]
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
            "Você é o desenvolvedor autônomo deste repositório. Leia o AGENTS.md "
            "e execute uma iteração do ciclo de decisão de devagent/CICLO.md, "
            "construindo o produto de PRODUTO.md: leia o estado, escolha o "
            "primeiro passo aplicável, entregue um PR e o relatório em "
            "docs/runs/. Não peça aprovação de plano e não faça perguntas: diante "
            "de ambiguidade, escolha a opção mais conservadora, registre a "
            "decisão no relatório e siga."
        ),
    },
    "auditor": {
        "titulo": "Auditor · produção",
        "prompt": (
            f"Você é o Auditor de Produção de {PRODUTO}, não o desenvolvedor. "
            "Leia e siga devagent/agents/auditor.md do começo ao fim. Ignore o "
            "ciclo de decisão de devagent/CICLO.md. Não altere o código da "
            "aplicação, os testes, as specs, AGENTS.md, PRODUTO.md nem "
            "devagent/. Entregue um único "
            'PR com título "auditoria: AAAA-MM-DD · N achados", contendo só '
            "arquivos de docs/auditoria/. Não peça aprovação e não faça perguntas."
        ),
    },
}

ESPECIALISTA = (
    "Você é {nome}, especialista em {tema} deste repositório, não o desenvolvedor. "
    "Leia e siga devagent/agents/especialistas.md: as regras comuns e a seção "
    "{nome}. Ignore o ciclo de decisão de devagent/CICLO.md. Se já existir PR aberto "
    "do agente, encerre sem mudanças. Entregue no máximo um PR, com título "
    'iniciado por "{prefixo}". Não peça aprovação e não faça perguntas.'
)
PERSONAS.update(
    {
        "seguranca": {
            "titulo": "Sentinel · segurança",
            "prompt": ESPECIALISTA.format(
                nome="Sentinel", tema="segurança", prefixo="🛡️ Sentinel:"
            ),
        },
        "design": {
            "titulo": "Palette · design",
            "prompt": ESPECIALISTA.format(
                nome="Palette", tema="design e experiência", prefixo="🎨 Palette:"
            ),
        },
        "performance": {
            "titulo": "Bolt · performance",
            "prompt": ESPECIALISTA.format(
                nome="Bolt", tema="performance", prefixo="⚡ Bolt:"
            ),
        },
    }
)
# Personas que alteram o código. Só uma delas trabalha por vez, para não
# abrirem PRs concorrentes (a regra de um PR aberto do agente por vez).
CONSTRUTORAS = {"desenvolvedor", "seguranca", "design", "performance"}

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


# O Jules limita tarefas por janela móvel de 24 h (15 no plano gratuito,
# 100 no Pro, 300 no Ultra). Se JULES_LIMITE_DIARIO estiver definido, o
# desenvolvedor deixa de criar sessões quando só restar a reserva para os
# especialistas e o auditor, que rodam uma vez por dia cada.
RESERVA_DIARIA = 4


def cota_esgotada(sessoes: list[dict[str, Any]]) -> bool:
    limite = os.environ.get("JULES_LIMITE_DIARIO", "").strip()
    if not limite.isdigit():
        return False
    corte = datetime.now(timezone.utc) - timedelta(hours=24)
    usadas = sum(1 for s in sessoes if _data(s, "createTime") >= corte)
    if usadas >= int(limite) - RESERVA_DIARIA:
        print(
            f"Cota: {usadas} sessões nas últimas 24 h, limite {limite} "
            f"com reserva de {RESERVA_DIARIA}. Desenvolvedor não iniciado."
        )
        return True
    return False


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
    grupo = CONSTRUTORAS if persona in CONSTRUTORAS else {persona}
    titulos = tuple(PERSONAS[x]["titulo"] for x in grupo)
    sessoes = sessoes_do_repo()
    if persona == "desenvolvedor" and cota_esgotada(sessoes):
        return 0
    for s in sessoes:
        if s.get("title", "").startswith(titulos) and s.get("state") in ATIVOS:
            print(f"Sessão ativa impede {persona}: {s.get('title')} ({s['state']})")
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
