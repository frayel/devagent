"""Avaliação do estado do sistema para a página /sistema (spec 082).

Junta o que é local (banco, agendador, registro das fontes, configuração,
fila de specs) com o retrato remoto do monitor (GitHub, Jules, Render) e
devolve uma lista de verificações com nível: ok, atenção, problema ou
inativo. Funções puras sobre os dados recebidos, com `agora` injetável, para
os testes não dependerem do relógio nem da rede.
"""

from __future__ import annotations

import os
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from app.services.cron import Cron
from app.banco import get_simbolos_suspensos

BRT = timezone(timedelta(hours=-3))
RAIZ = Path(__file__).resolve().parent.parent.parent

OK = "ok"
ATENCAO = "atencao"
PROBLEMA = "problema"
INATIVO = "inativo"
ROTULOS = {OK: "OK", ATENCAO: "Atenção", PROBLEMA: "Problema", INATIVO: "Inativo"}
PESO = {PROBLEMA: 3, ATENCAO: 2, OK: 1, INATIVO: 0}

# Integrações conhecidas: nome no registro → variável que a liga (None = sempre ligada).
INTEGRACOES: tuple[tuple[str, str | None, str], ...] = (
    ("MetaTrader 5", "MT5_API_URL", "fonte preferencial de cotações (mt5api)"),
    ("Yahoo Finance", None, "cotações e séries diárias"),
    ("brapi", "BRAPI_TOKEN", "cotações e rankings"),
    ("Gemini", "GEMINI_API_KEY", "extração de opiniões do Consultor"),
)

# Labels de issue que o ciclo do agente trata antes de tudo (CICLO.md, Passo 1).
# Elas já têm issue e workflow próprios (deploy-check.yml e a auditoria), que as
# abrem e fecham. Contadas aqui como Problema, viravam também um problema da
# issue `sistema-com-problema`, que só fechava depois delas: em 28/10 a #579
# listava a #577 como problema próprio. Ficam como Atenção, visíveis na página;
# o sintoma (coleta vazia, deploy falho) continua acusado pelos outros itens.
LABELS_COM_ISSUE_PROPRIA = ("deploy-falhou", "producao-incorreta")
LABELS_ATENCAO = ("prioridade", "tentativa-falhou", "bloqueado")

JULES_ESPERANDO = {"AWAITING_PLAN_APPROVAL", "AWAITING_USER_FEEDBACK"}
JULES_ATIVOS = JULES_ESPERANDO | {"QUEUED", "PLANNING", "IN_PROGRESS", "PAUSED"}


@dataclass
class Item:
    nome: str
    nivel: str
    resumo: str
    detalhe: str = ""
    quando: str | None = None  # ISO 8601
    desde: str | None = None
    link: str | None = None
    causa: str = ""
    acao: str = ""

    def __post_init__(self):
        texto = f"{self.resumo} {self.detalhe}".lower()
        if m := re.search(r"http (400|404|422)", texto):
            self.causa = f"pedido inválido ou ativo desconhecido (HTTP {m.group(1)})"
            self.acao = (
                f"corrigir o pedido no coletor {self.nome}; o servidor está respondendo"
            )
        elif m := re.search(r"http (5\d\d|429|401|403)", texto):
            self.causa = f"fonte indisponível ou recusando a chave (HTTP {m.group(1)})"
            self.acao = "aguardar, ou conferir a chave no Render"
        elif self.nivel != OK and re.search(
            r"\b(relation|column|does not exist)\b", texto
        ):
            self.causa = "esquema do banco incompleto"
            self.acao = "falta migração; ver spec do Consultor"
        elif "sem chamadas" in texto or "nunca chamada" in texto:
            self.causa = "configurada, mas nunca chamada"
            self.acao = "verificar o pipeline que a usa"
        elif (
            "fora do ar" in texto or "não respondeu" in texto or "não conecta" in texto
        ):
            self.causa = "fonte indisponível ou recusando a chave (rede)"
            self.acao = "aguardar, ou conferir a chave no Render"
        elif "abrir conexão com o postgres leva" in texto:
            self.causa = "conexão lenta com o banco (endereço externo ou outra região)"
            self.acao = (
                "usar no DATABASE_URL o endereço interno do Postgres, na mesma região"
            )
        elif self.nivel in (ATENCAO, PROBLEMA):
            self.causa = "causa não classificada"
            self.acao = "ver o detalhe e abrir issue"

    @property
    def rotulo(self) -> str:
        return ROTULOS[self.nivel]


# --------------------------------------------------------------------------
# Utilidades de tempo e texto
# --------------------------------------------------------------------------


def _dt(valor: str | datetime | None) -> datetime | None:
    if valor is None:
        return None
    if isinstance(valor, datetime):
        return valor if valor.tzinfo else valor.replace(tzinfo=timezone.utc)
    try:
        d = datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def hora_brt(valor: str | datetime | None, com_data: bool = True) -> str:
    d = _dt(valor)
    if d is None:
        return ""
    local = d.astimezone(BRT)
    return local.strftime("%d/%m/%Y %H:%M:%S" if com_data else "%H:%M:%S")


def ha_quanto(valor: str | datetime | None, agora: datetime) -> str:
    d = _dt(valor)
    if d is None:
        return "nunca"
    segundos = max(0, int((agora - d).total_seconds()))
    if segundos < 90:
        return "agora há pouco"
    minutos = segundos // 60
    if minutos < 90:
        return f"há {minutos} min"
    horas = minutos / 60
    if horas < 36:
        return f"há {horas:.0f} h".replace(".", ",")
    return f"há {horas / 24:.0f} dias"


def _idade(valor: str | datetime | None, agora: datetime) -> timedelta | None:
    d = _dt(valor)
    return None if d is None else agora - d


CONCLUSOES = {
    "success": "ok",
    "failure": "falhou",
    "cancelled": "cancelado",
    "skipped": "pulado",
    "timed_out": "estourou o tempo",
    "action_required": "esperando aprovação",
}


def conclusao(valor: str | None) -> str:
    return CONCLUSOES.get(valor or "", valor or "?")


def _pior(niveis: list[str]) -> str:
    return max(niveis, key=lambda n: PESO[n]) if niveis else OK


# --------------------------------------------------------------------------
# Aplicação, banco e coleta (locais)
# --------------------------------------------------------------------------


def verificar_versao(
    remoto_github: dict[str, Any] | None, sha_local: str | None, agora: datetime
) -> list[Item]:
    producao = (remoto_github or {}).get("producao")
    main = (remoto_github or {}).get("main")
    sha = (producao or {}).get("sha") or sha_local
    if not sha:
        return [
            Item(
                "Versão em produção",
                INATIVO,
                "commit desconhecido",
                "Fora do Render e sem checkout git, não há como saber o commit.",
            )
        ]
    itens = [
        Item(
            "Versão em produção",
            OK,
            sha[:7] + (f" · {hora_brt(producao['data'])}" if producao else ""),
            (producao or {}).get("mensagem", ""),
            (producao or {}).get("data"),
            (producao or {}).get("url"),
        )
    ]
    if producao is None or main is None:
        return itens
    atras = int(producao.get("atras", 0))
    if atras == 0:
        itens.append(
            Item("Deploy", OK, "em dia com a main", "", main["data"], main.get("url"))
        )
        return itens
    espera = _idade(main["data"], agora) or timedelta(0)
    nivel = OK if espera < timedelta(minutes=20) else ATENCAO
    if espera >= timedelta(hours=1):
        nivel = PROBLEMA
    resumo = f"main tem {atras} commit{'s' if atras > 1 else ''} sem deploy"
    detalhe = (
        f"O último commit da main ({main['sha'][:7]}) é de {hora_brt(main['data'])}, "
        f"{ha_quanto(main['data'], agora)}. O autoDeploy do Render costuma levar "
        "poucos minutos."
    )
    if nivel == OK:
        resumo = f"deploy em andamento ({atras} commit{'s' if atras > 1 else ''})"
    itens.append(Item("Deploy", nivel, resumo, detalhe, main["data"], main.get("url")))
    return itens


def verificar_render(remoto: dict[str, Any] | None, erro: str | None) -> list[Item]:
    if erro:
        return [Item("Render", ATENCAO, "API do Render não respondeu", erro)]
    if remoto is None:
        return [
            Item(
                "Render",
                INATIVO,
                "sem RENDER_API_KEY",
                "Defina RENDER_API_KEY no Render para ver o status do último deploy.",
            )
        ]
    d = remoto.get("deploy")
    if not d:
        return [Item("Render", ATENCAO, "nenhum deploy encontrado")]
    status = d.get("status") or "?"
    if status == "live":
        nivel = OK
    elif status in {"build_failed", "update_failed", "pre_deploy_failed"}:
        nivel = PROBLEMA
    elif status in {"canceled", "deactivated"}:
        nivel = ATENCAO
    else:
        nivel = OK  # build_in_progress, update_in_progress...
    quando = d.get("terminado_em") or d.get("criado_em")
    return [
        Item(
            "Último deploy no Render",
            nivel,
            f"{status} · {(d.get('sha') or '')[:7]}",
            d.get("mensagem") or "",
            quando,
        )
    ]


def verificar_instancia(inicio: datetime, agora: datetime) -> Item:
    return Item(
        "Instância",
        OK,
        f"no ar desde {hora_brt(inicio)}, {ha_quanto(inicio, agora)}",
        "No plano gratuito o Render hiberna o serviço sem visitas; ao acordar, a "
        "coleta e o registro das integrações recomeçam.",
        inicio.isoformat(),
    )


def verificar_historico_pregoes(datas: list[str], agora: datetime) -> Item:
    from app.calendario import pregao_anterior, ultimo_pregao_fechado

    if not datas:
        return Item(
            "Histórico de pregões",
            PROBLEMA,
            "sem registros",
            "Nenhum snapshot encontrado.",
        )

    # The seletor lists 5 previous pregoes + today/last closed.
    u = ultimo_pregao_fechado(agora)
    esperados = [u.strftime("%Y-%m-%d")]
    curr = u
    for _ in range(4):
        curr = pregao_anterior(curr)
        esperados.append(curr.strftime("%Y-%m-%d"))

    falhas = []
    for esp in esperados:
        if esp not in datas:
            falhas.append(esp)

    resumo = f"{len(datas)} pregões registrados"
    menor_data = min(datas)
    maior_data = max(datas)
    detalhe = f"Do {menor_data[8:10]}/{menor_data[5:7]} ao {maior_data[8:10]}/{maior_data[5:7]}."

    if falhas:
        detalhe += f" Faltam snapshots na janela recente: {', '.join(falhas)}"
        return Item("Histórico de pregões", ATENCAO, resumo, detalhe)

    return Item("Histórico de pregões", OK, resumo, detalhe)


CONEXAO_LENTA_MS = 500


def verificar_banco(info: dict[str, Any]) -> Item:
    if info.get("erro"):
        return Item("Banco de dados", PROBLEMA, "não conecta", info["erro"])
    # Versão e tamanho do banco em uso, para quem troca de provedor ver na hora
    # o que está conectado.
    tipo = f"{info['tipo']} {info['versao']}" if info.get("versao") else info["tipo"]
    resumo = f"{tipo} · {info.get('tamanho', '?')} · {info.get('latencia_ms', 0)} ms"
    if info["tipo"] == "SQLite" and info.get("database_url"):
        return Item(
            "Banco de dados",
            ATENCAO,
            resumo,
            "DATABASE_URL está configurado, mas o Postgres não respondeu quando a instância subiu; "
            "a aplicação está gravando no SQLite local, que se perde quando o Render reinicia. "
            "Reinicie o serviço depois de conferir o Postgres.",
        )
    detalhe = f"{info.get('tabelas', 0)} tabelas · tamanho em disco: {info.get('tamanho', '?')}"
    if info.get("conexao_ms") is not None:
        detalhe += f" · abrir conexão: {info['conexao_ms']} ms"
    # Sem pool aberto ainda, a latência medida inclui abrir a conexão.
    abrir = info.get("conexao_ms", info.get("latencia_ms", 0))
    if info["tipo"] == "Postgres" and abrir >= CONEXAO_LENTA_MS:
        return Item(
            "Banco de dados",
            ATENCAO,
            resumo,
            f"{detalhe}. Abrir conexão com o Postgres leva {abrir} ms, e cada página "
            "faz várias leituras. Confira se o DATABASE_URL usa o endereço interno do "
            "provedor e se o banco está na mesma região do serviço web.",
        )
    return Item("Banco de dados", OK, resumo, detalhe)


def verificar_agendador(
    ligada: bool,
    estado: dict[str, Any],
    esperado: timedelta,
    inicio: datetime,
    agora: datetime,
) -> list[Item]:
    if not ligada:
        return [
            Item(
                "Agendador da coleta",
                INATIVO,
                "desligado",
                "COLETA_AUTOMATICA=0: nenhum painel é atualizado.",
            )
        ]
    ultima = estado.get("ultima_coleta")
    itens: list[Item] = []
    if ultima is None:
        rodando_ha = agora - inicio
        nivel = ATENCAO if rodando_ha > timedelta(minutes=15) else OK
        itens.append(
            Item(
                "Agendador da coleta",
                nivel,
                "primeira rodada em andamento",
                "A primeira coleta começa quando o serviço sobe e leva alguns minutos.",
            )
        )
    else:
        idade = _idade(ultima, agora) or timedelta(0)
        tolerancia = esperado * 2 + timedelta(minutes=10)
        nivel = OK
        if idade > tolerancia:
            nivel = ATENCAO
        if idade > esperado * 4 + timedelta(minutes=10):
            nivel = PROBLEMA
        itens.append(
            Item(
                "Agendador da coleta",
                nivel,
                f"última rodada {ha_quanto(ultima, agora)}",
                f"Intervalo agora: {int(esperado.total_seconds() // 60)} min.",
                ultima,
            )
        )
    erro = estado.get("ultimo_erro")
    if erro:
        itens.append(
            Item(
                "Erro na última rodada",
                ATENCAO,
                str(erro)[:120],
                estado.get("detalhes") or "",
                ultima,
            )
        )
    return itens


def verificar_paineis_vazios(
    vazios: dict[str, int], horas: int, rodadas: dict[str, int] | None = None
) -> Item:
    if not vazios:
        return Item(
            "Painéis sem dados", OK, f"nenhuma coleta vazia nas últimas {horas} h"
        )
    rodadas = rodadas or {}
    # Painel vazio em todas as rodadas da janela (ao menos 3) está quebrado,
    # não oscilando: nenhuma fonte entregou o dado nenhuma vez.
    quebrados = sorted(
        p for p, n in vazios.items() if rodadas.get(p, 0) >= 3 and n >= rodadas[p]
    )
    ordem = sorted(vazios.items(), key=lambda kv: (-kv[1], kv[0]))
    lista = ", ".join(
        f"{p} ({n}×" + (f" em {rodadas[p]} rodadas)" if p in rodadas else ")")
        for p, n in ordem
    )
    if quebrados:
        return Item(
            "Painéis sem dados",
            PROBLEMA,
            f"{len(quebrados)} sempre vazio{'s' if len(quebrados) > 1 else ''}: "
            + ", ".join(quebrados),
            f"Vazios em todas as rodadas das últimas {horas} h: o coletor não "
            f"obtém o dado de nenhuma fonte. Todos os vazios: {lista}",
        )
    return Item(
        "Painéis sem dados",
        ATENCAO,
        f"{len(vazios)} painel{'s' if len(vazios) > 1 else ''} vazio{'s' if len(vazios) > 1 else ''} nas últimas {horas} h",
        lista,
    )


def verificar_tempo_coleta(tempos: dict[str, float]) -> Item:
    if not tempos:
        return Item("Duração da coleta", INATIVO, "sem medições")
    total = sum(tempos.values())
    lentos = sorted(tempos.items(), key=lambda kv: -kv[1])[:3]
    detalhe = "Mais lentos: " + ", ".join(
        f"{p} {s:.0f} s".replace(".", ",") for p, s in lentos
    )
    nivel = ATENCAO if total > 600 else OK
    return Item(
        "Duração da coleta",
        nivel,
        f"rodada completa em {total / 60:.1f} min".replace(".", ","),
        detalhe,
    )


def verificar_integracoes(
    fontes: dict[str, Any],
    pausa_mt5: tuple[float, str] | None,
    ambiente: dict[str, str],
    agora: datetime,
    modelo_gemini: str | None = None,
) -> list[Item]:
    itens: list[Item] = []
    conhecidas = set()
    for nome, variavel, papel in INTEGRACOES:
        conhecidas.add(nome)
        fonte = fontes.get(nome)
        if nome == "Gemini" and modelo_gemini:
            papel = f"{papel}. Modelo: {modelo_gemini}"
        configurada = variavel is None or bool(ambiente.get(variavel, "").strip())
        if not configurada and fonte is None:
            itens.append(Item(nome, INATIVO, f"sem {variavel}", papel))
            continue
        if nome == "MetaTrader 5" and pausa_mt5 is not None:
            restante, motivo = pausa_mt5
            itens.append(
                Item(
                    nome,
                    PROBLEMA,
                    "fora do ar, em pausa",
                    f"{motivo}. Nova tentativa em {restante / 60:.0f} min; enquanto isso "
                    "os painéis usam as outras fontes.",
                    fonte.ultima_falha.isoformat()
                    if fonte and fonte.ultima_falha
                    else None,
                )
            )
            continue
        itens.append(_item_da_fonte(nome, fonte, papel, agora))
    for nome, fonte in sorted(fontes.items()):
        if nome not in conhecidas:
            itens.append(_item_da_fonte(nome, fonte, "", agora))
    return itens


def _item_da_fonte(nome: str, fonte: Any, papel: str, agora: datetime) -> Item:
    if fonte is None or not fonte.recentes:
        return Item(nome, INATIVO, "sem chamadas desde a partida", papel)
    recentes = fonte.recentes
    graves = getattr(fonte, "graves", None) or [not r for r in recentes]
    falhas_recentes = recentes.count(False)

    nivel = OK
    texto_problema = ""
    endpoints_com_problema = []

    # Avaliação por endpoint
    if hasattr(fonte, "endpoints"):
        for ep_path, ep_data in fonte.endpoints.items():
            if ep_data.get("falhas", 0) >= 3 and ep_data.get("ultimo_status") == 404:
                simbolos_ok = ep_data.get("simbolos_ok", set())
                if len(simbolos_ok) > 0 or ep_data.get("falhas", 0) >= 3:
                    endpoints_com_problema.append(ep_path)

    ultimas = recentes[-5:]
    if endpoints_com_problema:
        nivel = PROBLEMA
        texto_problema = (
            f"o endpoint {endpoints_com_problema[0]} parece ter mudado ou saído do ar"
        )
    elif len(ultimas) >= 3 and not any(ultimas) and any(graves[-5:]):
        nivel = PROBLEMA
    elif not recentes[-1] or falhas_recentes / len(recentes) >= 0.3:
        nivel = ATENCAO

    total = fonte.sucessos + fonte.falhas
    resumo = f"{fonte.sucessos} de {total} chamadas ok"
    if fonte.ultimo_sucesso:
        resumo += f" · última ok {ha_quanto(fonte.ultimo_sucesso, agora)}"

    detalhe = papel

    if nome == "Yahoo Finance":
        suspensos = get_simbolos_suspensos()
        suspensos_yahoo = [s["simbolo"] for s in suspensos if s["fonte"] == "yfinance"]
        if suspensos_yahoo:
            nivel = _pior([nivel, ATENCAO])
            alerta = f"Sem cotação no Yahoo: {', '.join(suspensos_yahoo)}. Verifique a composição do Ibovespa."
            detalhe = f"{papel}. {alerta}" if papel else alerta

    if nome == "Yahoo Finance":
        suspensos = get_simbolos_suspensos()
        suspensos_yahoo = [s["simbolo"] for s in suspensos if s["fonte"] == "yfinance"]
        if suspensos_yahoo:
            nivel = _pior([nivel, ATENCAO])
            alerta = f"Sem cotação no Yahoo: {', '.join(suspensos_yahoo)}. Verifique a composição do Ibovespa."
            detalhe = f"{papel}. {alerta}" if papel else alerta

    if nome == "Yahoo Finance":
        suspensos = get_simbolos_suspensos()
        suspensos_yahoo = [s["simbolo"] for s in suspensos if s["fonte"] == "yfinance"]
        if suspensos_yahoo:
            nivel = _pior([nivel, ATENCAO])
            alerta = f"Sem cotação no Yahoo: {', '.join(suspensos_yahoo)}. Verifique a composição do Ibovespa."
            detalhe = f"{papel}. {alerta}" if papel else alerta

    if nome == "Yahoo Finance":
        suspensos = get_simbolos_suspensos()
        suspensos_yahoo = [s["simbolo"] for s in suspensos if s["fonte"] == "yfinance"]
        if suspensos_yahoo:
            nivel = _pior([nivel, ATENCAO])
            alerta = f"Sem cotação no Yahoo: {', '.join(suspensos_yahoo)}. Verifique a composição do Ibovespa."
            detalhe = f"{papel}. {alerta}" if papel else alerta
    if texto_problema:
        detalhe = f"{papel}. {texto_problema}" if papel else texto_problema
    elif fonte.ultima_falha:
        erro = f"Última falha {hora_brt(fonte.ultima_falha)}: {fonte.ultimo_erro}"

        ep_infos = []
        if hasattr(fonte, "endpoints") and fonte.endpoints:
            eps_ordenados = sorted(
                fonte.endpoints.items(),
                key=lambda x: x[1].get("falhas", 0),
                reverse=True,
            )
            for ep_path, ep_data in eps_ordenados[:3]:
                if ep_data.get("falhas", 0) > 0:
                    status = ep_data.get("ultimo_status") or "?"
                    corpo = ep_data.get("ultimo_corpo") or ""
                    ep_infos.append(f"[{ep_path} status {status}: {corpo}]")

        if ep_infos:
            erro += " " + " ".join(ep_infos)

        detalhe = f"{papel}. {erro}" if papel else erro

    quando = max(
        (d for d in (fonte.ultimo_sucesso, fonte.ultima_falha) if d), default=None
    )
    return Item(nome, nivel, resumo, detalhe, quando.isoformat() if quando else None)


# --------------------------------------------------------------------------
# Fluxo de desenvolvimento (retrato remoto)
# --------------------------------------------------------------------------


def verificar_github_api(
    github: dict[str, Any] | None, erro: str | None, atualizado_em: str | None
) -> Item:
    if erro and github is None:
        return Item("API do GitHub", PROBLEMA, "sem dados do GitHub", erro)
    if github is None:
        return Item(
            "API do GitHub", INATIVO, "primeira leitura em andamento", "", atualizado_em
        )
    limite = github.get("limite") or {}
    resumo = f"{limite.get('restante', '?')} de {limite.get('total', '?')} consultas restantes"
    detalhe = (
        ""
        if github.get("com_token")
        else "Sem GITHUB_TOKEN: o GitHub limita a 60 consultas por hora, então o "
        "retrato é refeito a cada 20 min."
    )
    if erro:
        return Item(
            "API do GitHub",
            ATENCAO,
            "última leitura falhou",
            f"{erro}. Os dados abaixo são da leitura anterior.",
            atualizado_em,
        )
    return Item("API do GitHub", OK, resumo, detalhe, atualizado_em)


def _runs_do(github: dict[str, Any], caminho: str) -> list[dict[str, Any]]:
    runs = [r for r in github.get("runs", []) if r["caminho"] == caminho]
    return sorted(runs, key=lambda r: r["criado_em"] or "", reverse=True)


def verificar_rodadas_jules(
    github: dict[str, Any], intervalo_min: int, agora: datetime
) -> Item:
    runs = [
        r
        for r in _runs_do(github, ".github/workflows/jules.yml")
        if r["evento"] == "workflow_dispatch"
    ]
    nome = "Disparo das rodadas (cron-job.org)"
    if not runs:
        return Item(
            nome,
            PROBLEMA,
            "nenhum disparo recente do jules.yml",
            "O cron-job.org dispara o workflow Jules por workflow_dispatch.",
        )
    ultimo = runs[0]
    idade = _idade(ultimo["criado_em"], agora) or timedelta(0)
    nivel = OK
    if idade > timedelta(minutes=intervalo_min * 3):
        nivel = ATENCAO
    if idade > timedelta(minutes=max(30, intervalo_min * 6)):
        nivel = PROBLEMA
    concluidos = [r for r in runs if r["status"] == "completed"][:10]
    falhas = [r for r in concluidos if r["conclusao"] == "failure"]
    if concluidos[:3] and all(r["conclusao"] == "failure" for r in concluidos[:3]):
        nivel = PROBLEMA
    elif falhas:
        nivel = _pior([nivel, ATENCAO])
    detalhe = (
        f"Esperado a cada {intervalo_min} min. "
        f"{len(falhas)} falha{'s' if len(falhas) != 1 else ''} nos últimos "
        f"{len(concluidos)} disparos."
    )
    if nivel != OK and idade > timedelta(minutes=intervalo_min * 3):
        detalhe += " O cron-job.org parou de disparar ou o GitHub recusou o pedido."
    return Item(
        nome,
        nivel,
        f"último {ha_quanto(ultimo['criado_em'], agora)}",
        detalhe,
        ultimo["criado_em"],
        ultimo.get("url"),
    )


def verificar_sessoes_jules(
    jules: dict[str, Any] | None, erro: str | None, limite: int, agora: datetime
) -> Item:
    nome = "Sessões do Jules"
    if erro:
        return Item(nome, ATENCAO, "API do Jules não respondeu", erro)
    if jules is None:
        return Item(
            nome,
            INATIVO,
            "sem JULES_API_KEY",
            "Defina JULES_API_KEY no Render para ver as sessões ativas e a cota.",
        )
    sessoes = jules.get("sessoes", [])
    ativas = [s for s in sessoes if s["estado"] in JULES_ATIVOS]
    dia = [
        s
        for s in sessoes
        if (_idade(s["criada_em"], agora) or timedelta.max) < timedelta(hours=24)
    ]
    falhas = [s for s in dia if s["estado"] == "FAILED"]
    esperando = [
        s
        for s in ativas
        if s["estado"] in JULES_ESPERANDO
        and (_idade(s["atualizada_em"], agora) or timedelta(0)) > timedelta(minutes=30)
    ]
    paradas = [
        s
        for s in ativas
        if (_idade(s["atualizada_em"], agora) or timedelta(0)) > timedelta(hours=3)
    ]
    nivel = OK
    notas = []
    if esperando:
        nivel = ATENCAO
        notas.append(f"{len(esperando)} esperando resposta há mais de 30 min")
    if paradas:
        nivel = ATENCAO
        notas.append(f"{len(paradas)} sem atualização há mais de 3 h")
    if falhas:
        nivel = ATENCAO
        notas.append(f"{len(falhas)} falharam nas últimas 24 h")
    if limite and len(dia) >= limite:
        nivel = PROBLEMA
        notas.append("cota diária esgotada")
    resumo = f"{len(ativas)} ativa{'s' if len(ativas) != 1 else ''} · {len(dia)}"
    resumo += f" de {limite} em 24 h" if limite else " em 24 h"
    titulos = "; ".join(f"{s['titulo']} ({s['estado']})" for s in ativas[:3])
    detalhe = ". ".join(filter(None, ["; ".join(notas), titulos]))
    return Item(nome, nivel, resumo, detalhe)


def verificar_workflows(github: dict[str, Any], agora: datetime) -> list[Item]:
    itens = []
    for wf in github.get("workflows", []):
        if wf["arquivo"] == "jules.yml":
            continue
        runs = [
            r for r in _runs_do(github, wf["caminho"]) if r["status"] == "completed"
        ]
        ultimo = runs[0] if runs else None
        nivel = OK
        partes: list[str] = []
        detalhe: list[str] = []
        if ultimo is None:
            nivel = INATIVO
            partes.append("sem execução recente")
        else:
            partes.append(
                f"{conclusao(ultimo['conclusao'])} {ha_quanto(ultimo['criado_em'], agora)}"
            )
            if ultimo["conclusao"] == "failure":
                # Falha no PR é o CI fazendo seu trabalho; na main ou num
                # agendamento, é o sistema quebrado.
                nivel = ATENCAO if ultimo["evento"] == "pull_request" else PROBLEMA
                detalhe.append(f"Falhou no evento {ultimo['evento']}.")
        if wf["crons"]:
            agendado = (github.get("ultimo_agendado") or {}).get(wf["caminho"])
            perdidos = disparos_perdidos(wf["crons"], agendado, agora)
            if agendado:
                detalhe.append(
                    f"Último agendado: {hora_brt(agendado['criado_em'])} "
                    f"({conclusao(agendado['conclusao'] or agendado['status'])})."
                )
            if perdidos >= 3:
                nivel = _pior([nivel, ATENCAO])
                partes.append(f"{perdidos} agendamentos não rodaram")
            if agendado and agendado["conclusao"] == "failure":
                nivel = PROBLEMA
        itens.append(
            Item(
                wf["nome"],
                nivel,
                " · ".join(partes),
                " ".join(detalhe),
                ultimo["criado_em"] if ultimo else None,
                ultimo.get("url") if ultimo else None,
            )
        )
    ci_main = [
        r
        for r in _runs_do(github, ".github/workflows/ci.yml")
        if r["evento"] == "push" and r["status"] == "completed"
    ]
    if ci_main:
        r = ci_main[0]
        nivel = PROBLEMA if r["conclusao"] == "failure" else OK
        itens.insert(
            0,
            Item(
                "CI na main",
                nivel,
                f"{conclusao(r['conclusao'])} {ha_quanto(r['criado_em'], agora)}",
                "",
                r["criado_em"],
                r.get("url"),
            ),
        )
    return itens


def disparos_perdidos(
    crons: list[str], agendado: dict[str, Any] | None, agora: datetime
) -> int:
    """Quantos disparos do cron deveriam ter acontecido sem execução.

    Conta os horários entre a última execução agendada (ou 7 dias atrás) e
    uma hora antes de agora; a folga de uma hora cobre o atraso normal do
    GitHub. Olha no máximo 7 dias para trás.
    """
    fim = agora - timedelta(hours=1)
    inicio = agora - timedelta(days=7)
    ultimo = _dt(agendado["criado_em"]) if agendado else None
    if ultimo and ultimo > inicio:
        inicio = ultimo
    if inicio >= fim:
        return 0
    total = 0
    for expr in crons:
        try:
            total += len(Cron(expr).disparos(inicio, fim))
        except ValueError:
            continue
    return total


def verificar_prs(github: dict[str, Any], agora: datetime) -> Item:
    prs = sorted(github.get("prs", []), key=lambda p: p["criado_em"])
    if not prs:
        return Item("PRs abertos", OK, "nenhum PR aberto")
    mais_antigo = prs[0]
    idade = _idade(mais_antigo["criado_em"], agora) or timedelta(0)
    nivel = OK
    if idade > timedelta(hours=3):
        nivel = ATENCAO
    if idade > timedelta(hours=12):
        nivel = PROBLEMA
    detalhe = "; ".join(
        f"#{p['numero']} {p['titulo']} ({ha_quanto(p['criado_em'], agora)})"
        for p in prs[:5]
    )
    return Item(
        "PRs abertos",
        nivel,
        f"{len(prs)} aberto{'s' if len(prs) > 1 else ''}, o mais antigo "
        f"{ha_quanto(mais_antigo['criado_em'], agora)}",
        detalhe,
        mais_antigo["criado_em"],
        mais_antigo["url"],
    )


def verificar_issues(github: dict[str, Any], agora: datetime) -> Item:
    nivel = OK
    linhas = []
    for issue in github.get("issues", []):
        labels = set(issue["labels"])
        if not labels & set(LABELS_COM_ISSUE_PROPRIA + LABELS_ATENCAO):
            continue
        nivel = _pior([nivel, ATENCAO])
        marca = ", ".join(
            sorted(labels & set(LABELS_COM_ISSUE_PROPRIA + LABELS_ATENCAO))
        )
        linhas.append(f"#{issue['numero']} [{marca}] {issue['titulo']}")
    if not linhas:
        return Item("Issues que pedem ação", OK, "nenhuma")
    return Item(
        "Issues que pedem ação",
        nivel,
        f"{len(linhas)} aberta{'s' if len(linhas) > 1 else ''}",
        "; ".join(linhas[:6]),
    )


def verificar_atividade(github: dict[str, Any], agora: datetime) -> Item:
    main = github.get("main")
    if not main:
        return Item("Última entrega na main", INATIVO, "sem dados")
    idade = _idade(main["data"], agora) or timedelta(0)
    nivel = OK
    if idade > timedelta(hours=12):
        nivel = ATENCAO
    if idade > timedelta(hours=48):
        nivel = PROBLEMA
    return Item(
        "Última entrega na main",
        nivel,
        f"{main['sha'][:7]} {ha_quanto(main['data'], agora)}",
        main.get("mensagem", ""),
        main["data"],
        main.get("url"),
    )


def verificar_fila(prontas: list[str]) -> Item:
    if not prontas:
        return Item(
            "Fila de specs",
            OK,
            "vazia",
            "Sem spec pronta, a próxima rodada escreve uma (Passo 7).",
        )
    return Item(
        "Fila de specs",
        OK,
        f"{len(prontas)} pronta{'s' if len(prontas) > 1 else ''}",
        f"Próxima: {prontas[0]}",
    )


# --------------------------------------------------------------------------
# Montagem
# --------------------------------------------------------------------------


def specs_prontas(raiz: Path = RAIZ) -> list[str]:
    status = re.compile(r"^status:\s*ready\s*$", re.MULTILINE | re.IGNORECASE)
    pasta = raiz / "docs" / "specs"
    if not pasta.is_dir():
        return []

    def chave(p: Path) -> tuple[int, str]:
        m = re.match(r"0*(\d+)([a-z]*)", p.name)
        return (int(m.group(1)), m.group(2)) if m else (10**9, p.name)

    prontas = [p for p in pasta.glob("*.md") if status.search(p.read_text("utf-8"))]
    return [p.stem for p in sorted(prontas, key=chave)]


def resumo_geral(grupos: list[dict[str, Any]]) -> dict[str, Any]:
    contagem = {PROBLEMA: 0, ATENCAO: 0, OK: 0, INATIVO: 0}
    pendentes: list[dict[str, Any]] = []
    for g in grupos:
        for item in g["itens"]:
            contagem[item["nivel"]] += 1
            if item["nivel"] in (PROBLEMA, ATENCAO):
                pendentes.append({**item, "grupo": g["titulo"]})
    pendentes.sort(key=lambda i: -PESO[i["nivel"]])
    if contagem[PROBLEMA]:
        nivel = PROBLEMA
        n = contagem[PROBLEMA]
        frase = f"{n} problema{'s' if n > 1 else ''}"
    elif contagem[ATENCAO]:
        nivel = ATENCAO
        n = contagem[ATENCAO]
        frase = f"{n} ponto{'s' if n > 1 else ''} de atenção"
    else:
        nivel = OK
        frase = "tudo funcionando"
    return {
        "nivel": nivel,
        "rotulo": ROTULOS[nivel],
        "frase": frase,
        "contagem": contagem,
        "pendentes": pendentes,
    }


def _grupo(titulo: str, itens: list[Item]) -> dict[str, Any]:
    return {
        "titulo": titulo,
        "nivel": _pior([i.nivel for i in itens]),
        "itens": [{**asdict(i), "rotulo": i.rotulo} for i in itens],
    }


def montar(
    *,
    agora: datetime,
    inicio: datetime,
    remoto: dict[str, Any],
    sha_local: str | None,
    banco: dict[str, Any],
    coleta_ligada: bool,
    estado_coleta: dict[str, Any],
    intervalo_coleta: timedelta,
    vazios: dict[str, int],
    horas_vazios: int,
    rodadas: dict[str, int] | None = None,
    tempos: dict[str, float],
    historico_pregoes: list[str],
    fontes: dict[str, Any],
    pausa_mt5: tuple[float, str] | None,
    prontas: list[str],
    ambiente: dict[str, str] | None = None,
    monitor_ligado: bool = False,
    modelo_gemini: str | None = None,
) -> dict[str, Any]:
    ambiente = dict(os.environ) if ambiente is None else ambiente
    github = remoto.get("github")
    intervalo_jules = int(ambiente.get("JULES_DISPARO_MINUTOS", "5") or 5)
    limite_jules = ambiente.get("JULES_LIMITE_DIARIO", "").strip()

    aplicacao = verificar_versao(github, sha_local, agora)
    aplicacao += verificar_render(remoto.get("render"), remoto.get("render_erro"))
    aplicacao.append(verificar_instancia(inicio, agora))
    aplicacao.append(verificar_banco(banco))
    aplicacao.append(verificar_historico_pregoes(historico_pregoes, agora))

    coleta = verificar_agendador(
        coleta_ligada, estado_coleta, intervalo_coleta, inicio, agora
    )
    coleta.append(verificar_paineis_vazios(vazios, horas_vazios, rodadas))
    coleta.append(verificar_tempo_coleta(tempos))

    integracoes = verificar_integracoes(
        fontes, pausa_mt5, ambiente, agora, modelo_gemini
    )

    desenvolvimento = [
        verificar_github_api(
            github, remoto.get("github_erro"), remoto.get("atualizado_em")
        )
    ]
    workflows: list[Item] = []
    if github:
        desenvolvimento += [
            verificar_rodadas_jules(github, intervalo_jules, agora),
            verificar_sessoes_jules(
                remoto.get("jules"),
                remoto.get("jules_erro"),
                int(limite_jules) if limite_jules.isdigit() else 0,
                agora,
            ),
            verificar_prs(github, agora),
            verificar_issues(github, agora),
            verificar_atividade(github, agora),
        ]
        workflows = verificar_workflows(github, agora)
    desenvolvimento.append(verificar_fila(prontas))

    grupos = [
        _grupo("Aplicação e banco", aplicacao),
        _grupo("Coleta", coleta),
        _grupo("Integrações externas", integracoes),
        _grupo("Fluxo de desenvolvimento", desenvolvimento),
    ]
    if workflows:
        grupos.append(_grupo("Workflows do GitHub", workflows))

    if "_alertas_desde" in remoto:
        for g in grupos:
            for i in g["itens"]:
                chave = f"{g['titulo']}/{i['nome']}"
                if remoto["_alertas_desde"] and chave in remoto["_alertas_desde"]:
                    i["desde"] = remoto["_alertas_desde"][chave]
                    from datetime import datetime

                    dt = datetime.fromisoformat(i["desde"])
                    i["resumo"] = f"(desde {dt.strftime('%d/%m %H:%M')}) " + i["resumo"]

    return {
        "gerado_em": agora.isoformat(),
        "remoto_em": remoto.get("atualizado_em"),
        # Contrato do núcleo (devagent/saude.py, ADR 016): o monitor ainda não
        # leu GitHub, Jules e Render desde que a instância subiu.
        "parcial": monitor_ligado and not remoto.get("atualizado_em"),
        "geral": resumo_geral(grupos),
        "grupos": grupos,
    }
