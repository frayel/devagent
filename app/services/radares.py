"""Os 20 radares da aba Alertas: com alertas, sem alertas, desatualizado ou indisponível (spec 150).

Cada radar aparece uma vez na aba: como card com alertas ou como nome na seção
"Sem alertas". A classificação segue a ordem da spec: payload ausente é
indisponível; coleta mais velha que o TTL durante o pregão é desatualizada;
lista vazia é "sem alertas"; o resto é card com alertas.
"""

from __future__ import annotations

from datetime import datetime
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
