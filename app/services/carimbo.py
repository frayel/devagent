"""Carimbo de cada card: de qual pregão é o número e quando foi coletado (spec 141).

Um helper único formata o horário no fuso de exibição, decide a data do pregão
do número (a da última barra, não a do relógio) e diz se o card está
desatualizado. A idade só vira "desatualizado" durante o pregão: fora dele, o
rótulo é o da sessão (spec 077).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from collections.abc import Sequence
from typing import Any

from app import calendario

try:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

    try:
        FUSO: Any = ZoneInfo("America/Sao_Paulo")
    except ZoneInfoNotFoundError:  # pragma: no cover - imagem sem tzdata
        FUSO = timezone(timedelta(hours=-3))
except ImportError:  # pragma: no cover
    FUSO = timezone(timedelta(hours=-3))

TTL_MINUTOS_PADRAO = 30
"""TTL do guia (docs/DESIGN.md): 30 minutos durante o pregão."""

TTL_MINUTOS: dict[str, int] = {
    "ibovespa": TTL_MINUTOS_PADRAO,
    "mare": TTL_MINUTOS_PADRAO,
    "altas_baixas": TTL_MINUTOS_PADRAO,
    "motores_indice": TTL_MINUTOS_PADRAO,
}

CARDS_CRITICOS = ("ibovespa", "mare", "altas_baixas", "motores_indice")


def ttl_minutos(chave: str) -> int:
    return TTL_MINUTOS.get(chave, TTL_MINUTOS_PADRAO)


def formatar(dt: datetime) -> str:
    """`dd/mm/aaaa HH:MM BRT` no fuso de exibição."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(FUSO).strftime("%d/%m/%Y %H:%M BRT")


def _ler_data(valor: Any) -> date | None:
    if isinstance(valor, datetime):
        return valor.astimezone(FUSO).date()
    if isinstance(valor, date):
        return valor
    if not isinstance(valor, str) or not valor:
        return None
    for formato in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(valor[:10], formato).date()
        except ValueError:
            continue
    return None


def pregao_de(timestamp: datetime | None, ultima_barra: Any = None) -> date | None:
    """Data do pregão a que o número pertence.

    Usa a data da última barra quando existe e não é posterior à coleta. Sem ela,
    deriva da coleta: dia sem pregão ou coleta antes da abertura pertencem ao
    pregão anterior. Nunca promove um D−1 a D0.
    """
    local = None
    if timestamp is not None:
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        local = timestamp.astimezone(FUSO)
    barra = _ler_data(ultima_barra)
    if barra is not None and (local is None or barra <= local.date()):
        return barra
    if local is None:
        return None
    d = local.date()
    if not calendario.e_pregao(d) or local.time() < calendario.ABERTURA:
        return calendario.pregao_anterior(d)
    return d


def no_pregao(agora: datetime) -> bool:
    """Dia útil do calendário, entre a abertura e o fechamento."""
    local = agora.astimezone(FUSO)
    return (
        calendario.e_pregao(local.date())
        and calendario.ABERTURA <= local.time() <= calendario.FECHAMENTO
    )


def desatualizado(coletado_em: datetime | None, agora: datetime, chave: str) -> bool:
    """Durante o pregão, idade maior que o TTL da chave. Fora dele, nunca."""
    if coletado_em is None or not no_pregao(agora):
        return False
    if coletado_em.tzinfo is None:
        coletado_em = coletado_em.replace(tzinfo=timezone.utc)
    return agora - coletado_em > timedelta(minutes=ttl_minutos(chave))


def carimbo(
    chave: str,
    timestamp: datetime | None,
    fonte: str | None,
    agora: datetime,
    ultima_barra: Any = None,
) -> dict[str, Any]:
    """O que o card precisa para o rodapé, o selo e o cabeçalho."""
    pregao = pregao_de(timestamp, ultima_barra)
    horario = formatar(timestamp) if timestamp else ""
    pregao_str = pregao.strftime("%d/%m/%Y") if pregao else ""
    # Rodapé: a data do pregão aparece sempre; se a coleta foi noutro dia,
    # o pregão do número vem escrito ao lado (nenhum D−1 passa por D0).
    rodape = horario
    if horario and pregao_str and not horario.startswith(pregao_str):
        rodape = f"{horario} · pregão {pregao_str}"
    return {
        "chave": chave,
        "pregao": pregao,
        "pregao_iso": pregao.isoformat() if pregao else None,
        "pregao_str": pregao_str,
        "horario": horario,
        "rodape": rodape,
        "fonte": fonte or "",
        "desatualizado": desatualizado(timestamp, agora, chave),
    }


def pregoes_mistos(carimbos: Sequence[dict[str, Any] | None]) -> bool:
    datas = {c["pregao"] for c in carimbos if c and c.get("pregao")}
    return len(datas) > 1


def rotulo_cabecalho(
    carimbos: Sequence[dict[str, Any] | None], agora: datetime, mercado_aberto: bool
) -> str:
    """Pregão em leitura e as-of, a partir dos cards críticos.

    Pregões divergentes: "pregões mistos", e cada card conserva a própria data.
    """
    validos = [c for c in carimbos if c and c.get("pregao")]
    if not validos:
        return ""
    if pregoes_mistos(validos):
        datas = sorted({c["pregao"] for c in validos})
        lista = ", ".join(d.strftime("%d/%m/%Y") for d in datas)
        return f"Pregões mistos ({lista}) · cada card mostra a data do seu número"
    pregao = validos[0]["pregao"]
    hoje = agora.astimezone(FUSO).date()
    if no_pregao(agora) and pregao == hoje:
        asof = validos[0]["horario"].split(" ", 1)[-1] if validos[0]["horario"] else ""
        return f"Ao vivo · pregão de {pregao.strftime('%d/%m/%Y')}" + (
            f" · atualizado às {asof}" if asof else ""
        )
    esperado = (
        calendario.pregao_corrente(agora)
        if mercado_aberto
        else calendario.ultimo_pregao_fechado(agora)
    )
    rotulo = f"Fechamento de {pregao.strftime('%d/%m/%Y')}"
    if pregao < esperado:
        rotulo += " · pregão anterior"
    return rotulo
