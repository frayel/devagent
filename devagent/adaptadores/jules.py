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
    python -m devagent.adaptadores.jules iniciar especificador | revisor | verificador
    python -m devagent.adaptadores.jules destravar   # aprova planos e responde perguntas
    python -m devagent.adaptadores.jules rodada      # uma volta: inicia a próxima sessão se o caminho
                                                     # estiver livre, destrava e sai (cron-job.org, ADRs 010 e 012)
    python -m devagent.adaptadores.jules vigiar      # laço contínuo; sem uso no Actions, cobra minuto parado
    python -m devagent.adaptadores.jules listar
    python -m devagent.adaptadores.jules encerrar <id da sessão ou URL da tarefa>
    python -m devagent.adaptadores.jules iniciar auditor --dry-run

Variáveis de ambiente:
    JULES_API_KEY   chave criada em https://jules.google.com/settings#api
    JULES_SOURCE    opcional; padrão sources/github/<repositorio do devagent.toml>
    GH_TOKEN        opcional; lê o estado do PR de cada sessão (sem ele, a API
                    pública do GitHub, com limite menor)
    JULES_LIMITE_DIARIO      opcional; tarefas do plano por 24 h. Define a cota e
                             o ritmo do desenvolvedor (ADR 012)
    JULES_INTERVALO_MINUTOS  opcional; intervalo mínimo entre sessões do
                             desenvolvedor, no lugar do ritmo calculado pela cota

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
from pathlib import Path
from typing import Any

from devagent.conferir_pr import documentos
from devagent.config import PROJETO
from devagent.estado_github import _get as github_get
from devagent.estado_github import eh_do_agente, status_ci
from devagent.fila_specs import (
    LABEL_PRIORIDADE,
    LABEL_TENTATIVA,
    fila_da_revisao,
    instrucao,
    proximo_numero,
    spec_para_dividir,
    specs_prontas,
)
from devagent.raias import DESENVOLVIMENTO, raia_do_titulo

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
    "{nome}. Se já existir PR aberto do agente, encerre sem mudanças. Entregue no "
    'máximo um PR, com título iniciado por "{prefixo}". Se não achar nada que '
    "valha um PR, não abra PR só com o diário: siga a regra 7, que passa a sessão "
    "para o ciclo do desenvolvedor de devagent/CICLO.md. Não peça aprovação e não "
    "faça perguntas."
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
# Raias paralelas (ADR 021): cada uma tem no máximo uma sessão ativa e um PR
# aberto, e escreve só na sua faixa (devagent/raias.py). Correm ao lado do
# desenvolvimento sem disputar arquivos com ele.
RAIA_PARALELA = (
    "Você é o {nome} deste repositório, não o desenvolvedor. Leia e siga a seção "
    "{nome} de devagent/agents/raias.md, do começo ao fim. Ignore o ciclo de "
    "decisão de devagent/CICLO.md. Altere só o que a sua raia pode alterar e "
    'entregue no máximo um PR, com título iniciado por "{prefixo}". Não peça '
    "aprovação e não faça perguntas."
)
PERSONAS.update(
    {
        "especificador": {
            "titulo": "Especificador · spec",
            "prompt": RAIA_PARALELA.format(nome="Especificador", prefixo="spec:"),
            "raia": "especificacao",
        },
        "revisor": {
            "titulo": "Revisor · spec",
            "prompt": RAIA_PARALELA.format(nome="Revisor", prefixo="revisão:"),
            "raia": "revisao",
        },
        "verificador": {
            "titulo": "Verificador · geral",
            "prompt": RAIA_PARALELA.format(nome="Verificador", prefixo="verificação:"),
            "raia": "verificacao",
        },
    }
)
PARALELAS = ("especificador", "revisor", "verificador")

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


# Sessão ativa sem nenhuma atualização há este tempo está morta. A mediana
# de uma sessão até o PR é ~30 min (ADR 013).
SESSAO_PARADA = timedelta(hours=3)


def motivo_de_zumbi(s: dict[str, Any], agora: datetime) -> str:
    """Por que uma sessão que a API diz ativa já não está trabalhando ("" se está).

    Em 18/10 a sessão do Sentinel do PR #335 continuou "ativa" depois do
    merge, porque a cobrança do guardião a reabriu e o Jules não a fechou.
    Como só uma sessão que altera código roda por vez, ela travou o ciclo das
    04h31 às 13h17 (BRT) e o Bolt perdeu o dia.
    """
    if s.get("state") not in ATIVOS:
        return ""
    url = pr_da_sessao(s)
    if url:
        pr = estado_do_pr(url)
        if pr is not None and not pr["aberto"]:
            return (
                f"O PR {url} já foi mesclado."
                if pr["mesclado"]
                else f"O PR {url} foi fechado; o trabalho segue pelo próximo ciclo."
            )
    parada = agora - _data(s, "updateTime")
    if parada >= SESSAO_PARADA:
        horas = parada.total_seconds() / 3600
        return f"A sessão está sem atualização há {horas:.1f} h e foi dada como parada."
    return ""


def encerrar_zumbis(sessoes: list[dict[str, Any]], agora: datetime) -> list[str]:
    """Encerra as sessões ativas que já não trabalham e devolve os nomes."""
    encerradas = []
    for s in sessoes:
        motivo = motivo_de_zumbi(s, agora)
        if motivo:
            print(
                f"Sessão zumbi: {s['name']} ({s.get('title', '')}, {s.get('state')}). {motivo}"
            )
            encerrar(s["name"], motivo)
            encerradas.append(s["name"])
    return encerradas


# Sessão que termina em FAILED (ADR 019). Em 21 e 22/10 as sessões das specs
# 074 e 076a pararam numa pergunta e o Jules encerrou a tarefa na mesma
# mensagem. O destravar só responde AWAITING_USER_FEEDBACK, então a resposta
# nunca chegava e a rodada seguinte abria outra sessão do zero, sem saber por
# que a anterior caiu.
JANELA_FALHA = timedelta(hours=6)
ESPERA_RETOMADA = timedelta(minutes=15)
MARCA_RETOMADA = "[retomada automática]"
RETOMADA_DE_FALHA = (
    f"{MARCA_RETOMADA} A tarefa parou numa pergunta e foi encerrada. Não há "
    "humano acompanhando esta sessão e ninguém vai responder: a resposta é sim. "
    "Siga com o que você mesmo propôs (se apresentou opções, fique com a que "
    "recomendou ou com a mais conservadora), registre a decisão no relatório e "
    "continue até abrir o PR. Não peça confirmação de novo."
)
MARCA_SESSAO = "<!-- jules-sessao: {nome} -->"
SPEC_DO_PROMPT = re.compile(r"próxima é (\S+?\.md)")


def atividades(nome: str) -> list[dict[str, Any]]:
    """Atividades da sessão, da mais antiga para a mais recente."""
    todas: list[dict[str, Any]] = []
    token = ""
    for _ in range(5):
        caminho = f"{nome}/activities?pageSize=100" + (
            f"&pageToken={token}" if token else ""
        )
        resp = chamar("GET", caminho)
        todas += resp.get("activities", [])
        token = resp.get("nextPageToken", "")
        if not token:
            break
    return sorted(todas, key=lambda a: a.get("createTime", ""))


def ultima_fala_do_agente(acts: list[dict[str, Any]]) -> str:
    for a in reversed(acts):
        texto = (a.get("agentMessaged") or {}).get("agentMessage")
        if texto:
            return str(texto)
    return ""


def motivo_da_falha(acts: list[dict[str, Any]]) -> str:
    for a in reversed(acts):
        if "sessionFailed" in a:
            return str((a.get("sessionFailed") or {}).get("reason") or "")
    return ""


def retomada_enviada_em(acts: list[dict[str, Any]]) -> datetime | None:
    for a in reversed(acts):
        texto = (a.get("userMessaged") or {}).get("userMessage") or ""
        if MARCA_RETOMADA in texto:
            return _data(a, "createTime")
    return None


def falha_registrada(nome: str) -> bool:
    """Já existe issue `tentativa-falhou` (aberta ou fechada) desta sessão."""
    marca = MARCA_SESSAO.format(nome=nome)
    brutas = github_get(
        f"/repos/{PROJETO['repositorio']}/issues"
        f"?state=all&labels={LABEL_TENTATIVA}&per_page=100"
    )
    return any(marca in (i.get("body") or "") for i in brutas)


def github_post(caminho: str, corpo: dict[str, Any]) -> Any:
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        raise OSError("GH_TOKEN ausente: não dá para abrir issue")
    req = urllib.request.Request(
        f"https://api.github.com{caminho}",
        data=json.dumps(corpo).encode(),
        method="POST",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode() or "{}")


def corpo_da_falha(s: dict[str, Any], acts: list[dict[str, Any]]) -> tuple[str, str]:
    """Título e corpo da issue `tentativa-falhou` de uma sessão que falhou."""
    nome = s["name"]
    ident = nome.rsplit("/", 1)[-1]
    m = SPEC_DO_PROMPT.search(s.get("prompt") or "")
    spec = m.group(1) if m else ""
    rotulo = spec.rsplit("/", 1)[-1].split("-", 1)[0] if spec else ""
    titulo = f"Tentativa falhou no Jules: {s.get('title', 'sessão')}" + (
        f" (spec {rotulo})" if rotulo else ""
    )
    fala = ultima_fala_do_agente(acts) or "(sem mensagem do agente)"
    motivo = motivo_da_falha(acts)
    corpo = (
        f"{MARCA_SESSAO.format(nome=nome)}\n"
        f"A sessão https://jules.google.com/session/{ident} terminou em `FAILED`"
        + (f" quando trabalhava em `{spec}`" if spec else "")
        + ". A retomada automática não a trouxe de volta.\n\n"
        + (f"**Motivo informado pelo Jules:** {motivo}\n\n" if motivo else "")
        + "**Última mensagem do agente:**\n\n"
        + "\n".join(f"> {linha}" for linha in fala[-4000:].splitlines())
        + "\n\nAntes de refazer este trabalho, leia a mensagem acima: ela diz onde "
        "a sessão travou e o que pretendia fazer. Não repita o caminho que falhou. "
        "O PR que concluir o trabalho deve conter `Closes` para esta issue."
    )
    return titulo, corpo


def registrar_falha(s: dict[str, Any], acts: list[dict[str, Any]]) -> None:
    if falha_registrada(s["name"]):
        return
    titulo, corpo = corpo_da_falha(s, acts)
    issue = github_post(
        f"/repos/{PROJETO['repositorio']}/issues",
        {"title": titulo, "body": corpo, "labels": [LABEL_TENTATIVA]},
    )
    print(f"Falha registrada: {s['name']} -> issue #{issue.get('number', '?')}")


def tratar_falhas(sessoes: list[dict[str, Any]], agora: datetime) -> bool:
    """Retoma ou registra as sessões nossas que falharam há pouco.

    Primeiro manda a resposta que a sessão não recebeu. Se ela continuar em
    FAILED depois de ESPERA_RETOMADA, ou se o Jules recusar a mensagem, abre a
    issue `tentativa-falhou` com a última fala do agente, só para sessões do
    desenvolvedor (as dos especialistas não têm spec a dividir).

    Devolve True enquanto alguma retomada está dentro do prazo: a rodada não
    inicia sessão nova para não competir com a que pode voltar.
    """
    nossas = tuple(p["titulo"] for p in PERSONAS.values())
    dev = PERSONAS["desenvolvedor"]["titulo"]
    # Só a retomada de quem altera código segura a próxima sessão dele; a de
    # uma raia paralela não trava o desenvolvimento (ADR 021).
    construtoras = tuple(PERSONAS[x]["titulo"] for x in CONSTRUTORAS)
    aguardar = False
    for s in sessoes:
        if s.get("state") != "FAILED" or not s.get("title", "").startswith(nossas):
            continue
        if agora - _data(s, "updateTime") > JANELA_FALHA:
            continue
        nome = s["name"]
        acts = atividades(nome)
        enviada = retomada_enviada_em(acts)
        recusada = False
        if enviada is None:
            try:
                chamar("POST", f"{nome}:sendMessage", {"prompt": RETOMADA_DE_FALHA})
                print(
                    f"Retomada enviada à sessão que falhou: {nome} ({s.get('title')})"
                )
                aguardar = aguardar or s.get("title", "").startswith(construtoras)
                continue
            except urllib.error.HTTPError as erro:
                print(f"Retomada recusada em {nome}: HTTP {erro.code}")
                recusada = True
        elif agora - enviada < ESPERA_RETOMADA:
            aguardar = aguardar or s.get("title", "").startswith(construtoras)
            continue
        if s.get("title", "").startswith(dev):
            registrar_falha(s, acts)
        elif not recusada:
            print(f"Sessão de especialista não voltou: {nome}")
    return aguardar


def issues_com_label(label: str) -> list[dict[str, Any]]:
    """Issues abertas com o label, no formato do estado_github (ADRs 018 e 020).

    Sem acesso ao GitHub, devolve lista vazia: a fila segue sem o desvio.
    """
    try:
        brutas = github_get(
            f"/repos/{PROJETO['repositorio']}/issues"
            f"?state=open&labels={label}&per_page=100"
        )
    except (urllib.error.URLError, OSError, ValueError):
        return []
    return [
        {
            "numero": i["number"],
            "titulo": i["title"],
            "labels": [lbl["name"] for lbl in i["labels"]],
            "corpo": i.get("body") or "",
        }
        for i in brutas
        if "pull_request" not in i
    ]


def issues_de_tentativa() -> list[dict[str, Any]]:
    return issues_com_label(LABEL_TENTATIVA)


def issues_de_prioridade() -> list[dict[str, Any]]:
    return issues_com_label(LABEL_PRIORIDADE)


def prompt_de(persona: str) -> str:
    """Prompt da sessão; o do desenvolvedor já traz a próxima spec da fila.

    A ordem do ciclo vive no CICLO.md, mas o agente já pulou o Passo 4 e
    escreveu spec nova com doze specs ready esperando (PR #356). Dizer no
    prompt qual spec é a próxima evita a escolha errada antes que ela aconteça
    (ADR 015).
    """
    texto = PERSONAS[persona]["prompt"]
    if persona in PARALELAS:
        extra = complemento_da_raia(persona)
        return f"{texto} {extra}" if extra else texto
    if persona != "desenvolvedor":
        return texto
    try:
        issues = issues_de_tentativa() + issues_de_prioridade()
        fila = instrucao(specs_prontas(), issues=issues)
    except OSError:
        fila = ""
    # O desenvolvimento não escreve spec (ADR 023): sem número reservado.
    return " ".join(t for t in (texto, fila) if t)


# "use o número 084" no prompt: o número de spec nova reservado para a sessão.
NUMERO_RESERVADO = re.compile(r"use o número (\d{3,4})\b")
# Reserva vale enquanto a sessão pode ter PR aberto com a spec nova.
JANELA_RESERVA = timedelta(hours=12)


def numeros_reservados(sessoes: list[dict[str, Any]], agora: datetime) -> set[int]:
    """Números de spec prometidos a sessões recentes que ainda podem usá-los."""
    reservados: set[int] = set()
    for s in sessoes:
        if agora - _data(s, "createTime") > JANELA_RESERVA:
            continue
        for m in NUMERO_RESERVADO.finditer(s.get("prompt") or ""):
            reservados.add(int(m.group(1)))
    return reservados


def numero_para_spec_nova(sessoes: list[dict[str, Any]] | None = None) -> str:
    """Próximo número livre na main, pulando os reservados a outras sessões.

    Sem a pasta de specs (projeto que ainda não as tem), não há reserva e o
    prompt fica no texto fixo, como no ADR 015.
    """
    if not (Path.cwd() / documentos()["specs"]).is_dir():
        return ""
    ocupados: set[int] = set()
    try:
        if sessoes is None and os.environ.get("JULES_API_KEY"):
            sessoes = sessoes_do_repo()
        ocupados = numeros_reservados(sessoes or [], datetime.now(timezone.utc))
    except (urllib.error.URLError, OSError, ValueError):
        pass
    try:
        return proximo_numero(ocupados=ocupados)
    except OSError:
        return ""


def _relativo(caminho: Path) -> str:
    try:
        return caminho.relative_to(Path.cwd()).as_posix()
    except ValueError:
        return caminho.as_posix()


def complemento_da_raia(persona: str) -> str:
    """O alvo concreto da sessão de uma raia paralela, decidido antes dela."""
    if persona == "especificador":
        numero = numero_para_spec_nova()
        if not numero:
            return ""
        return (
            f"Para a spec nova desta sessão, use o número {numero}: ele está "
            "reservado para ela."
        )
    if persona == "revisor":
        try:
            prontas = specs_prontas()
        except OSError:
            prontas = []
        dividir = spec_para_dividir(prontas, issues_de_tentativa())
        if dividir:
            spec, falhas = dividir
            fecha = " ".join(f"Closes #{n}" for n in falhas)
            return (
                f"A tarefa desta sessão é dividir {_relativo(spec)}: ela teve "
                f"tentativa fechada pelo guardião ({', '.join(f'#{n}' for n in falhas)}). "
                "Leia a issue, divida a spec em partes menores (cada parte já "
                "revisada), marque a original como `draft`, diga nela para onde foi "
                f"cada parte e ponha no corpo do PR: {fecha}. Não toque em "
                "nenhuma outra spec."
            )
        fila = fila_da_revisao(prontas)
        if not fila:
            return ""
        return (
            f"A spec a revisar nesta sessão é {_relativo(fila[0])}. Não toque em "
            "nenhuma outra spec."
        )
    if persona == "verificador":
        merges = merges_do_desenvolvimento(desde=ultima_verificacao())
        if not merges:
            return ""
        lista = ", ".join(f"#{pr['number']} ({pr['title']})" for pr in merges[:15])
        return f"Verifique o que estes PRs levaram à main: {lista}."
    return ""


def iniciar(persona: str, dry_run: bool) -> int:
    p = PERSONAS[persona]
    corpo = {
        "title": p["titulo"],
        "prompt": prompt_de(persona),
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
    if (persona == "desenvolvedor" or persona in PARALELAS) and cota_esgotada(sessoes):
        return 0
    agora = datetime.now(timezone.utc)
    for s in sessoes:
        if s.get("title", "").startswith(titulos) and s.get("state") in ATIVOS:
            if motivo_de_zumbi(s, agora):
                continue  # a rodada encerra; não deve travar a fila
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


# Persona de cada hora (UTC): a partir dessa hora, o especialista do dia é o
# primeiro da fila até rodar. Em BRT: Sentinel 03h, Bolt 09h, Palette 15h.
# O vigia (sem uso) ainda inicia uma persona por hora cheia.
PERSONA_DA_HORA = {6: "seguranca", 12: "performance", 18: "design"}

# PR com CI verde ainda não mesclado só é "travado" depois deste tempo
# (CICLO.md, Passo 2: o auto-merge falhou).
PR_VERDE_TRAVADO = timedelta(minutes=60)


def persona_da_vez(sessoes: list[dict[str, Any]], agora: datetime) -> str:
    """O especialista do dia cuja hora já chegou e que ainda não rodou desde
    ela; senão, o desenvolvedor. Um especialista que perde a hora porque o
    desenvolvedor estava ocupado entra assim que a sessão terminar."""
    for hora, persona in sorted(PERSONA_DA_HORA.items()):
        if agora.hour < hora:
            break
        desde = agora.replace(hour=hora, minute=0, second=0, microsecond=0)
        titulo = PERSONAS[persona]["titulo"]
        if not any(
            s.get("title", "").startswith(titulo) and _data(s, "createTime") >= desde
            for s in sessoes
        ):
            return persona
    return "desenvolvedor"


def intervalo_do_desenvolvedor() -> timedelta:
    """Menor espaço entre duas sessões do desenvolvedor.

    JULES_INTERVALO_MINUTOS manda, se existir. Senão, com JULES_LIMITE_DIARIO,
    a cota que sobra depois da reserva é espalhada pelas 24 h, para não ser
    gasta numa rajada e deixar o agente parado o resto do dia. Sem nenhuma
    das duas, não há espera: a próxima sessão começa quando a anterior acaba.
    """
    fixo = os.environ.get("JULES_INTERVALO_MINUTOS", "").strip()
    if fixo.isdigit():
        return timedelta(minutes=int(fixo))
    limite = os.environ.get("JULES_LIMITE_DIARIO", "").strip()
    if limite.isdigit() and int(limite) > RESERVA_DIARIA:
        return timedelta(minutes=24 * 60 / (int(limite) - RESERVA_DIARIA))
    return timedelta(0)


# PR com CI vermelho e atividade recente está sendo corrigido pela própria
# sessão (o CI Fixer do Jules ou a resposta à cobrança do guardião). Em 22/10
# a rodada abriu outra sessão para "destravar" o #414 às 18h; ela reimplementou
# a spec 076b do zero e abriu o #415 quando o #414 já tinha sido mesclado.
PR_EM_CORRECAO = timedelta(minutes=60)


def em_correcao(pr: dict[str, Any], agora: datetime) -> bool:
    atualizado = pr.get("updated_at")
    if not atualizado:
        return False
    return agora - _data({"createTime": atualizado}, "createTime") < PR_EM_CORRECAO


def sessao_viva_do_pr(pr: dict[str, Any], sessoes: list[dict[str, Any]]) -> bool:
    """Há sessão ativa do Jules cuja saída é este PR (quem de fato o corrige)."""
    url = pr.get("html_url")
    return any(
        s.get("state") in ATIVOS and url and pr_da_sessao(s) == url for s in sessoes
    )


def situacao_dos_prs(sessoes: list[dict[str, Any]] | None = None) -> tuple[str, str]:
    """('livre' | 'esperar' | 'travado', descrição) dos PRs abertos do agente.

    esperar: o CI ainda roda, ou passou há pouco e o auto-merge vai mesclar.
    Uma sessão nova agora só acharia o PR aberto e sairia sem entregar nada.
    Também espera o PR com CI vermelho que teve atividade (push, cobrança do
    guardião) há menos de PR_EM_CORRECAO: a sessão dona dele está corrigindo.
    Com `sessoes`, a espera "em correção" exige uma sessão ativa cuja saída é o
    PR; sem ela, o PR vermelho já fica travado e chama o desenvolvedor.
    travado: CI falhou sem atividade recente, ou verde há mais de
    PR_VERDE_TRAVADO; é trabalho do desenvolvedor (Passo 2), nunca de um
    especialista.
    """
    repo = PROJETO["repositorio"]
    agora = datetime.now(timezone.utc)
    travado = ""
    for pr in github_get(f"/repos/{repo}/pulls?state=open&per_page=50"):
        if not eh_do_agente(pr):
            continue
        ci = status_ci(repo, pr["head"]["sha"])
        idade = agora - _data({"createTime": pr.get("created_at")}, "createTime")
        desc = f"PR #{pr['number']} ({ci})"
        if ci in ("rodando", "sem_ci") or (ci == "passou" and idade < PR_VERDE_TRAVADO):
            return "esperar", desc
        # Com a lista de sessões em mãos, só espera se a sessão dona do PR
        # ainda está viva: sessão encerrada não responde à cobrança do guardião.
        if (
            ci.startswith("falhou")
            and em_correcao(pr, agora)
            and (sessoes is None or sessao_viva_do_pr(pr, sessoes))
        ):
            return "esperar", f"{desc}, em correção"
        travado = travado or desc
    return ("travado", travado) if travado else ("livre", "")


def motivo_para_esperar(
    persona: str, sessoes: list[dict[str, Any]], agora: datetime
) -> str:
    if persona != "desenvolvedor":
        return ""
    intervalo = intervalo_do_desenvolvedor()
    titulo = PERSONAS["desenvolvedor"]["titulo"]
    datas = [
        _data(s, "createTime") for s in sessoes if s.get("title", "").startswith(titulo)
    ]
    if datas and agora - max(datas) < intervalo:
        falta = intervalo - (agora - max(datas))
        return (
            f"desenvolvedor: ritmo da cota, próxima sessão em "
            f"{int(falta.total_seconds() // 60) + 1} min."
        )
    return ""


# --- Raias paralelas (ADR 021) -------------------------------------------

# O verificador olha o que o desenvolvimento entregou; uma volta por merge
# seria gastar a cota em diffs de uma linha. Junta o que chegou neste intervalo.
INTERVALO_VERIFICADOR = timedelta(minutes=90)
# Sem verificação anterior, olha só o que chegou à main neste período.
JANELA_PRIMEIRA_VERIFICACAO = timedelta(hours=24)
# Com a fila neste tamanho ou menor, o especificador prepara a próxima spec:
# a que sobra é a que o desenvolvimento está implementando.
FILA_PARA_ESPECIFICAR = 1


def ultima_sessao(persona: str, sessoes: list[dict[str, Any]]) -> datetime | None:
    titulo = PERSONAS[persona]["titulo"]
    datas = [
        _data(s, "createTime") for s in sessoes if s.get("title", "").startswith(titulo)
    ]
    return max(datas) if datas else None


def ultima_verificacao(sessoes: list[dict[str, Any]] | None = None) -> datetime:
    try:
        if sessoes is None and os.environ.get("JULES_API_KEY"):
            sessoes = sessoes_do_repo()
    except (urllib.error.URLError, OSError, ValueError):
        sessoes = None
    ultima = ultima_sessao("verificador", sessoes or [])
    return ultima or datetime.now(timezone.utc) - JANELA_PRIMEIRA_VERIFICACAO


def merges_do_desenvolvimento(desde: datetime) -> list[dict[str, Any]]:
    """PRs da raia de desenvolvimento mesclados depois de `desde`, mais novos antes."""
    try:
        prs = github_get(
            f"/repos/{PROJETO['repositorio']}/pulls"
            "?state=closed&sort=updated&direction=desc&per_page=50"
        )
    except (urllib.error.URLError, OSError, ValueError):
        return []
    return [
        pr
        for pr in prs
        if pr.get("merged_at")
        and _data({"createTime": pr["merged_at"]}, "createTime") > desde
        and raia_do_titulo(pr.get("title") or "") == DESENVOLVIMENTO
    ]


def raias_com_pr_aberto() -> set[str]:
    """Raias que já têm PR aberto: a sessão nova só acharia trabalho em curso."""
    abertos = github_get(
        f"/repos/{PROJETO['repositorio']}/pulls?state=open&per_page=50"
    )
    return {raia_do_titulo(pr.get("title") or "") for pr in abertos}


def raias_a_iniciar(
    sessoes: list[dict[str, Any]],
    agora: datetime,
    prontas: list[Path],
    em_revisao: list[Path],
    com_pr: set[str],
    merges_novos: int,
    dividir: bool = False,
) -> list[str]:
    """Quais raias paralelas abrem sessão nesta volta (decisão pura, testável).

    Cada raia tem no máximo uma sessão ativa e um PR aberto. Além disso:
    - especificador: a fila de specs ready chegou a FILA_PARA_ESPECIFICAR;
    - revisor: há spec ready esperando revisão, ou a próxima spec do
      desenvolvimento tem tentativa fechada e precisa ser dividida (ADR 023);
    - verificador: o desenvolvimento mesclou algo desde a última verificação,
      e ela foi há pelo menos INTERVALO_VERIFICADOR.
    """
    escolhidas = []
    for persona in PARALELAS:
        p = PERSONAS[persona]
        if p["raia"] in com_pr:
            continue
        if any(
            s.get("title", "").startswith(p["titulo"])
            and s.get("state") in ATIVOS
            and not motivo_de_zumbi(s, agora)
            for s in sessoes
        ):
            continue
        if persona == "especificador" and len(prontas) > FILA_PARA_ESPECIFICAR:
            continue
        if persona == "revisor" and not em_revisao and not dividir:
            continue
        if persona == "verificador":
            ultima = ultima_sessao("verificador", sessoes)
            if not merges_novos or (ultima and agora - ultima < INTERVALO_VERIFICADOR):
                continue
        escolhidas.append(persona)
    return escolhidas


def rodada_das_raias(sessoes: list[dict[str, Any]], agora: datetime) -> None:
    """Abre as sessões das raias paralelas que têm trabalho e caminho livre."""
    prontas = specs_prontas()
    em_revisao = fila_da_revisao(prontas)
    com_pr = raias_com_pr_aberto()
    ultima = ultima_sessao("verificador", sessoes)
    desde = ultima or agora - JANELA_PRIMEIRA_VERIFICACAO
    merges = len(merges_do_desenvolvimento(desde))
    dividir = spec_para_dividir(prontas, issues_de_tentativa()) is not None
    escolhidas = raias_a_iniciar(
        sessoes, agora, prontas, em_revisao, com_pr, merges, dividir
    )
    for persona in escolhidas:
        try:
            iniciar(persona, dry_run=False)
        except Exception as erro:  # noqa: BLE001
            print(f"::warning::iniciar {persona} falhou: {erro}")


def rodada(espera_minutos: int) -> int:
    """Uma volta só, em segundos, para o job do Actions não ficar ligado à toa.

    Inicia a próxima sessão assim que o caminho estiver livre (nenhuma sessão
    que altera código ativa, nenhum PR do agente esperando o merge, ritmo da
    cota respeitado) e destrava as sessões paradas. Não há mais uma sessão por
    hora: com o relógio externo chamando a cada poucos minutos, uma sessão que
    termina sem nada a fazer é seguida pela próxima na volta seguinte (ADR 012).
    Na mesma volta, cada raia paralela com trabalho e caminho livre ganha a
    sua sessão (ADR 021).
    """
    agora = datetime.now(timezone.utc)
    sessoes: list[dict[str, Any]] | None = None
    try:
        sessoes = sessoes_do_repo()
        mortas = set(encerrar_zumbis(sessoes, agora))
        for s in sessoes:
            if s.get("name") in mortas:
                s["state"] = "CANCELLED"
        rodada_do_desenvolvimento(sessoes, agora)
    except Exception as erro:  # noqa: BLE001
        print(f"::warning::rodada não iniciou sessão: {erro}")
    # As raias paralelas não dependem do PR do desenvolvimento nem da retomada
    # dele: correm na mesma volta, cada uma com a sua trava (ADR 021).
    if sessoes is not None:
        try:
            rodada_das_raias(sessoes, agora)
        except Exception as erro:  # noqa: BLE001
            print(f"::warning::raias paralelas não iniciadas: {erro}")
    return destravar(espera_minutos)


def rodada_do_desenvolvimento(sessoes: list[dict[str, Any]], agora: datetime) -> None:
    """A vez do desenvolvedor ou do especialista do dia, se o caminho estiver livre."""
    try:
        if tratar_falhas(sessoes, agora):
            print("Aguardando a retomada de uma sessão que falhou.")
            return
    except Exception as erro:  # noqa: BLE001
        print(f"::warning::tratar_falhas falhou: {erro}")
    persona = persona_da_vez(sessoes, agora)
    situacao, desc = situacao_dos_prs(sessoes)
    if situacao == "esperar":
        print(f"{persona}: aguardando o merge de {desc}.")
    else:
        if situacao == "travado" and persona != "desenvolvedor":
            print(f"{persona} adiado: {desc} precisa do desenvolvedor.")
            persona = "desenvolvedor"
        motivo = motivo_para_esperar(persona, sessoes, agora)
        if motivo:
            print(motivo)
        else:
            iniciar(persona, dry_run=False)


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
