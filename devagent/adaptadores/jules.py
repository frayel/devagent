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
    python -m devagent.adaptadores.jules rodada      # uma volta: persona da hora + destravar, e sai
                                                     # (chamada a cada 30 min pelo cron-job.org, ADR 010)
    python -m devagent.adaptadores.jules vigiar      # laço contínuo; sem uso no Actions, cobra minuto parado
    python -m devagent.adaptadores.jules listar
    python -m devagent.adaptadores.jules encerrar <id da sessão ou URL da tarefa>
    python -m devagent.adaptadores.jules iniciar auditor --dry-run

Variáveis de ambiente:
    JULES_API_KEY   chave criada em https://jules.google.com/settings#api
    JULES_SOURCE    opcional; padrão sources/github/<repositorio do devagent.toml>
    GH_TOKEN        opcional; lê o estado do PR de cada sessão (sem ele, a API
                    pública do GitHub, com limite menor)

O nome do produto e o repositório vêm do devagent.toml; os prompts só apontam
para os arquivos do núcleo (devagent/CICLO.md e devagent/agents/).

Só usa a biblioteca padrão.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
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

# O Jules às vezes encerra o turno anunciando o que vai fazer e pedindo
# confirmação ("posso seguir?"), mesmo com o prompt proibindo perguntas.
# A resposta confirma a decisão que ele já tomou; mandar escolher "a opção
# mais conservadora" o levava a perguntar de novo ou a não fazer nada.
RESPOSTA_PADRAO = (
    "Sim, siga. Não há humano acompanhando esta sessão e ninguém vai "
    "responder: execute agora o que você já decidiu ou propôs, sem pedir "
    "confirmação de novo. Se apresentou opções, fique com a que recomendou "
    "(ou com a mais conservadora, se não recomendou nenhuma). Registre a "
    "decisão no relatório ou no corpo do PR e continue até abrir o PR."
)

# Quando a sessão já abriu um PR, o ambiente dela pode ter sido reiniciado e
# perdido as alterações. "Sim, siga" a fazia recomeçar da main e refazer o
# trabalho; a resposta aponta a branch do PR, onde o trabalho está (ADR 009).
RESPOSTA_COM_PR = (
    "Sim, siga, mas nesta ordem. O trabalho desta sessão já está no PR {url}, "
    "na branch `{branch}`. Não recomece da `main` e não recrie a spec: rode "
    "`git fetch origin && git checkout -B {branch} origin/{branch}`, aplique "
    "nessa branch o que falta para o CI passar (o log está nos comentários do "
    "PR) e dê push nela. Não há humano acompanhando esta sessão e ninguém vai "
    "responder: não peça confirmação de novo."
)

# Sessão cujo PR foi fechado ou mesclado: o trabalho acabou ou foi entregue
# por outro PR. Responder "siga" a faria abrir um PR duplicado.
ENCERRAMENTO = (
    "Encerre esta tarefa agora, sem mais alterações, commits ou PRs. {motivo} "
    "Não responda, não peça confirmação e não recomece o trabalho."
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


def pr_da_sessao(s: dict[str, Any]) -> str | None:
    for saida in s.get("outputs") or []:
        url = (saida.get("pullRequest") or {}).get("url")
        if url:
            return str(url)
    return None


def estado_do_pr(url: str) -> dict[str, Any] | None:
    """Estado e branch de um PR do GitHub; None se não der para ler."""
    m = re.match(r"https://github\.com/([^/]+)/([^/]+)/pull/(\d+)", url)
    if not m:
        return None
    dono, repo, numero = m.groups()
    cab = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        cab["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(
        f"https://api.github.com/repos/{dono}/{repo}/pulls/{numero}", headers=cab
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            pr = json.loads(resp.read().decode())
    except (urllib.error.URLError, ValueError) as erro:
        print(f"::warning::estado de {url} ilegível: {erro}")
        return None
    return {
        "aberto": pr.get("state") == "open",
        "mesclado": bool(pr.get("merged")),
        "branch": (pr.get("head") or {}).get("ref", ""),
    }


def nome_da_sessao(alvo: str) -> str:
    """Aceita o id, `sessions/<id>` ou a URL da tarefa no site do Jules."""
    alvo = alvo.strip().rstrip("/")
    ident = alvo.rsplit("/", 1)[-1]
    if not ident:
        raise ValueError(f"sessão inválida: {alvo!r}")
    return f"sessions/{ident}"


def encerrar(alvo: str, motivo: str = "") -> int:
    nome = nome_da_sessao(alvo)
    texto = ENCERRAMENTO.format(motivo=motivo or "O dono do produto encerrou a tarefa.")
    try:
        chamar("POST", f"{nome}:sendMessage", {"prompt": texto.strip()})
        print(f"Encerramento enviado: {nome}")
    except urllib.error.HTTPError as erro:
        print(f"::warning::mensagem de encerramento falhou em {nome}: HTTP {erro.code}")
    # Apagar a sessão a tira da fila; nem toda versão da API aceita.
    try:
        chamar("DELETE", nome)
        print(f"Sessão apagada: {nome}")
    except urllib.error.HTTPError as erro:
        print(f"Sessão não apagada (HTTP {erro.code}); a mensagem basta para pará-la.")
    return 0


def resposta_para(s: dict[str, Any]) -> tuple[str, str]:
    """O que dizer a uma sessão parada numa pergunta: ('responder'|'encerrar', texto)."""
    url = pr_da_sessao(s)
    if not url:
        return "responder", RESPOSTA_PADRAO
    pr = estado_do_pr(url)
    if pr is None:
        return "responder", RESPOSTA_PADRAO
    if not pr["aberto"]:
        motivo = (
            f"O PR {url} já foi mesclado."
            if pr["mesclado"]
            else f"O PR {url} foi fechado; o trabalho segue por outro PR ou pelo próximo ciclo."
        )
        return "encerrar", motivo
    return "responder", RESPOSTA_COM_PR.format(url=url, branch=pr["branch"])


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
                acao, texto = resposta_para(s)
                if acao == "encerrar":
                    encerrar(nome, texto)
                else:
                    chamar("POST", f"{nome}:sendMessage", {"prompt": texto})
                    print(f"Pergunta respondida: {nome} ({s.get('title', '')})")
    return 0


# Persona de cada hora (UTC) no relógio próprio. Nas demais horas, o
# desenvolvedor. Em BRT: Sentinel 03h, Bolt 09h, Palette 15h.
PERSONA_DA_HORA = {6: "seguranca", 12: "performance", 18: "design"}


def ja_iniciada_nesta_hora() -> bool:
    hora_atual = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    titulos = tuple(PERSONAS[x]["titulo"] for x in CONSTRUTORAS)
    return any(
        s.get("title", "").startswith(titulos) and _data(s, "createTime") >= hora_atual
        for s in sessoes_do_repo()
    )


def rodada(espera_minutos: int) -> int:
    """Uma volta só: inicia a persona da hora (se ainda não foi iniciada nesta
    hora) e destrava as sessões paradas. Leva segundos e termina, para o job
    do Actions não ficar ligado à toa entre uma volta e outra.
    """
    persona = PERSONA_DA_HORA.get(datetime.now(timezone.utc).hour, "desenvolvedor")
    try:
        if ja_iniciada_nesta_hora():
            print(f"{persona}: já iniciada nesta hora.")
        else:
            iniciar(persona, dry_run=False)
    except Exception as erro:  # noqa: BLE001
        print(f"::warning::iniciar {persona} falhou: {erro}")
    return destravar(espera_minutos)


def vigiar(duracao_minutos: int, intervalo_minutos: int, espera_minutos: int) -> int:
    """Laço que substitui o cron do GitHub, que descarta a maioria dos disparos.

    A cada hora nova, tenta iniciar a persona da hora (as travas de sessão
    ativa e de cota continuam valendo). A cada intervalo, destrava. Um erro
    numa volta não encerra o laço.
    """
    fim = datetime.now(timezone.utc) + timedelta(minutes=duracao_minutos)
    ultima_hora: int | None = None
    # Na troca de turno entre vigias, não inicia de novo a persona da hora
    # se o vigia anterior já a iniciou nesta mesma hora.
    try:
        hora_atual = datetime.now(timezone.utc).replace(
            minute=0, second=0, microsecond=0
        )
        titulos = tuple(PERSONAS[x]["titulo"] for x in CONSTRUTORAS)
        if any(
            s.get("title", "").startswith(titulos)
            and _data(s, "createTime") >= hora_atual
            for s in sessoes_do_repo()
        ):
            ultima_hora = hora_atual.hour
    except Exception as erro:  # noqa: BLE001
        print(f"::warning::leitura inicial das sessões falhou: {erro}")
    while True:
        agora = datetime.now(timezone.utc)
        if agora >= fim:
            return 0
        if agora.hour != ultima_hora:
            persona = PERSONA_DA_HORA.get(agora.hour, "desenvolvedor")
            try:
                iniciar(persona, dry_run=False)
                ultima_hora = agora.hour
            except Exception as erro:  # noqa: BLE001
                print(f"::warning::iniciar {persona} falhou: {erro}")
        try:
            destravar(espera_minutos)
        except Exception as erro:  # noqa: BLE001
            print(f"::warning::destravar falhou: {erro}")
        sys.stdout.flush()
        restante = (fim - datetime.now(timezone.utc)).total_seconds()
        time.sleep(max(0.0, min(intervalo_minutos * 60, restante)))


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
    d.add_argument("--espera-minutos", type=int, default=5)
    v = sub.add_parser("vigiar")
    v.add_argument("--duracao-minutos", type=int, default=340)
    v.add_argument("--intervalo-minutos", type=int, default=5)
    v.add_argument("--espera-minutos", type=int, default=5)
    r = sub.add_parser("rodada")
    r.add_argument("--espera-minutos", type=int, default=5)
    sub.add_parser("listar")
    e = sub.add_parser("encerrar")
    e.add_argument("sessao", help="id da sessão, sessions/<id> ou URL da tarefa")
    e.add_argument("--motivo", default="")
    args = ap.parse_args(argv)
    if args.cmd == "iniciar":
        return iniciar(args.persona, args.dry_run)
    if args.cmd == "destravar":
        return destravar(args.espera_minutos)
    if args.cmd == "encerrar":
        return encerrar(args.sessao, args.motivo)
    if args.cmd == "rodada":
        return rodada(args.espera_minutos)
    if args.cmd == "vigiar":
        return vigiar(args.duracao_minutos, args.intervalo_minutos, args.espera_minutos)
    return listar()


if __name__ == "__main__":
    sys.exit(main())
