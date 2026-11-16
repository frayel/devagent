"""Os 20 radares da aba Alertas: com alertas, sem alertas, desatualizado ou indisponível (spec 150).

Cada radar aparece uma vez na aba: como card com alertas ou como nome na seção
"Sem alertas". A classificação segue a ordem da spec: payload ausente é
indisponível; coleta mais velha que o TTL durante o pregão é desatualizada;
lista vazia é "sem alertas"; o resto é card com alertas.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from app.services import carimbo

# (chave no contexto do template, título do card, campo da lista)
RADARES: tuple[tuple[str, str, str], ...] = (
    ("volume_alerts", "Radar de volume", "alerts"),
    ("variacao_subita", "Variação Súbita", "alertas"),
    ("concentracao_ordens", "Concentração de Ordens", "alertas"),
    ("exaustao_alta", "Exaustão de Alta", "alertas"),
    ("exaustao_queda", "Exaustão de Queda", "alertas"),
    ("exaustao_tendencia", "Exaustão de Tendência", "alertas"),
    ("radar_absorcao_cruzada", "Radar de Absorção Cruzada", "alertas"),
    ("liquidez_abertura", "Radar de Liquidez", "alertas"),
    ("radar_congestionamento", "Radar de Congestionamento", "alertas"),
    ("faca_caindo", "Radar de Faca Caindo", "alertas"),
    ("anomalias_spread", "Anomalias de Spread", "alertas"),
    ("short_squeeze", "Radar de Short Squeeze", "alertas"),
    ("falso_rompimento", "Falso Rompimento", "alertas"),
    ("radar_divergencia_volume", "Divergência Volume/Preço", "alertas"),
    ("esforco_resultado", "Índice de Esforço vs Resultado", "alertas"),
    ("scanner_capitulacao", "Scanner de Capitulação", "alertas"),
    ("armadilha_abertura", "Armadilhas de Abertura", "alertas"),
    ("compradores_fundo", "Compradores de Fundo", "alertas"),
    ("radar_anomalia_fechamento", "Radar de Anomalia de Fechamento", "alertas"),
    ("radar_inflexao", "Radar de Inflexão", "alertas"),
)

# Chaves de RADARES cujo snapshot tem outro nome (spec 166); as outras usam a própria chave.
SNAPSHOT_DO_RADAR: dict[str, str] = {"short_squeeze": "radar_short_squeeze"}


def escondidos(payloads: dict[str, Any]) -> list[str]:
    """Chaves de RADARES que a aba Alertas esconderia, na ordem declarada (spec 166).

    Recebe os payloads crus de `ler_snapshot`, indexados pela chave de RADARES.
    Escondido: payload ausente ou falso, `<campo>_json` ausente, que não é texto
    ou não é JSON válido, ou JSON falso (lista vazia, `null`). Não olha horário.
    """
    resultado: list[str] = []
    for chave, _nome, campo in RADARES:
        payload = payloads.get(chave)
        bruto = payload.get(f"{campo}_json") if isinstance(payload, dict) else None
        lista: Any = None
        if payload and isinstance(bruto, str):
            try:
                lista = json.loads(bruto)
            except ValueError:
                lista = None
        if not lista:
            resultado.append(chave)
    return resultado


COM_ALERTAS = "com_alertas"
SEM_ALERTAS = "sem_alertas"
DESATUALIZADO = "desatualizado"
INDISPONIVEL = "indisponivel"

_CLASSE_BASE = "visao-micro alertas"


def _campo(payload: Any, nome: str) -> Any:
    if isinstance(payload, dict):
        return payload.get(nome)
    return getattr(payload, nome, None)


def classificar(
    payload: Any, chave: str, agora: datetime, is_historical: bool
) -> tuple[str, datetime | None]:
    """Estado do radar e o horário bruto da coleta (quando existe)."""
    if not payload:
        return INDISPONIVEL, None
    timestamp = _campo(payload, "timestamp")
    if not isinstance(timestamp, datetime):
        timestamp = None
    if not is_historical and carimbo.desatualizado(timestamp, agora, chave):
        return DESATUALIZADO, timestamp
    if not _campo(payload, campo_da(chave)):
        return SEM_ALERTAS, timestamp
    return COM_ALERTAS, timestamp


def campo_da(chave: str) -> str:
    for c, _nome, campo in RADARES:
        if c == chave:
            return campo
    raise KeyError(chave)


def _hora(timestamp: datetime | None) -> str:
    if timestamp is None:
        return ""
    return carimbo.formatar(timestamp)[11:16]


def resumo(
    contexto: dict[str, Any],
    agora: datetime,
    is_historical: bool,
    mostrar_vazios: bool,
) -> dict[str, Any]:
    """O que a aba Alertas precisa: a classe de cada card e a seção "Sem alertas"."""
    classes: dict[str, str] = {}
    sem_alertas: list[str] = []
    outros: list[dict[str, str]] = []
    for chave, nome, _campo_lista in RADARES:
        estado, timestamp = classificar(
            contexto.get(chave), chave, agora, is_historical
        )
        if estado == COM_ALERTAS:
            classes[chave] = _CLASSE_BASE
        elif estado == SEM_ALERTAS:
            sem_alertas.append(nome)
            classes[chave] = f"{_CLASSE_BASE} radar-vazio" + (
                "" if mostrar_vazios else " escondido"
            )
        elif estado == DESATUALIZADO:
            outros.append({"nome": nome, "estado": estado, "hora": _hora(timestamp)})
            classes[chave] = f"{_CLASSE_BASE} escondido"
        else:
            outros.append({"nome": nome, "estado": estado, "hora": ""})
            classes[chave] = f"{_CLASSE_BASE} escondido"
    return {
        "classes": classes,
        "sem_alertas": sem_alertas,
        "outros": outros,
        "mostrar_vazios": mostrar_vazios,
        "secao": bool(sem_alertas or outros),
    }


MINIMO_CONFLUENCIA = 2
MAX_LINHAS_CONFLUENCIA = 10


def _ticker(item: Any) -> str | None:
    """Ticker normalizado: sem espaços, maiúsculo, sem o sufixo `.SA`."""
    bruto = _campo(item, "ticker")
    if not isinstance(bruto, str):
        return None
    ticker = bruto.strip().upper()
    if ticker.endswith(".SA"):
        ticker = ticker[:-3]
    return ticker or None


def _utc(ts: datetime) -> datetime:
    return ts if ts.tzinfo is not None else ts.replace(tzinfo=timezone.utc)


def _texto_excedentes(resto: list[dict[str, Any]]) -> str:
    """`+N ações em K radares` para as linhas que passam do limite."""
    if not resto:
        return ""
    contagens = sorted({len(linha["radares"]) for linha in resto})
    radares = (
        f"{contagens[0]} radares"
        if len(contagens) == 1
        else f"{contagens[0]} a {contagens[-1]} radares"
    )
    acoes = "ação" if len(resto) == 1 else "ações"
    return f"+{len(resto)} {acoes} em {radares}"


def confluencia(
    contexto: dict[str, Any], agora: datetime, is_historical: bool
) -> dict[str, Any]:
    """As ações citadas por 2 ou mais radares com coleta em dia (spec 155).

    Conta citações; não pesa radares nem recomenda. Radar desatualizado ou
    indisponível fica fora da contagem e de `lidos`.
    """
    citacoes: dict[str, list[str]] = {}
    horarios: dict[str, datetime | None] = {}
    lidos = 0
    for chave, nome, campo in RADARES:
        payload = contexto.get(chave)
        estado, ts = classificar(payload, chave, agora, is_historical)
        if estado in (COM_ALERTAS, SEM_ALERTAS):
            lidos += 1
        if estado != COM_ALERTAS:
            continue
        horarios[nome] = ts
        tickers = {_ticker(item) for item in (_campo(payload, campo) or [])}
        for ticker in tickers:
            if ticker:
                citacoes.setdefault(ticker, []).append(nome)

    linhas = sorted(
        (
            {"ticker": ticker, "radares": nomes}
            for ticker, nomes in citacoes.items()
            if len(nomes) >= MINIMO_CONFLUENCIA
        ),
        key=lambda linha: (-len(linha["radares"]), linha["ticker"]),
    )
    citados = {nome for linha in linhas for nome in linha["radares"]}
    carimbos = [_utc(ts) for nome in citados if (ts := horarios.get(nome))]
    resto = linhas[MAX_LINHAS_CONFLUENCIA:]
    return {
        "acoes": linhas[:MAX_LINHAS_CONFLUENCIA],
        "excedentes": len(resto),
        "texto_excedentes": _texto_excedentes(resto),
        "lidos": lidos,
        "horario": min(carimbos) if carimbos else None,
        "horario_texto": carimbo.formatar(min(carimbos)) if carimbos else "",
    }
