import json
from typing import Any
from datetime import datetime, timezone, timedelta

from app.database import get_latest_highlights_data
from app.services.sparkline import build_sparkline


def format_asset(asset: dict[str, Any]) -> dict[str, Any]:
    price = asset.get("price", 0.0)
    change_percent = asset.get("change_percent", 0.0)

    price_formatted = (
        f"R$ {price:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    )

    change_formatted = f"{change_percent:.2f}%".replace(".", ",")
    if change_percent > 0:
        change_formatted = f"+{change_formatted}"

    sparkline = build_sparkline(asset.get("sparkline", []))

    return {
        "ticker": asset.get("ticker", ""),
        "price": price,
        "price_formatted": price_formatted,
        "change_percent": change_percent,
        "change_percent_formatted": change_formatted,
        "is_positive": change_percent > 0,
        "is_negative": change_percent < 0,
        "sparkline": sparkline,
        "base": asset.get("base"),
        "fonte": asset.get("fonte"),
        "janela": asset.get("janela"),
    }


def get_highlights_view_data() -> dict[str, Any] | None:
    data = get_latest_highlights_data()
    if not data:
        return None

    try:
        highs = json.loads(data.highs_json)
        lows = json.loads(data.lows_json)
    except json.JSONDecodeError:
        return None

    em_revisao_raw = []
    if getattr(data, "em_revisao_json", None):
        try:
            em_revisao_raw = json.loads(data.em_revisao_json)
        except json.JSONDecodeError:
            em_revisao_raw = []

    ausentes_tickers = []
    if getattr(data, "ausentes_json", None):
        try:
            ausentes_tickers = json.loads(data.ausentes_json)
        except json.JSONDecodeError:
            ausentes_tickers = []

    highs_formatted = [format_asset(h) for h in highs]
    lows_formatted = [format_asset(low) for low in lows]
    em_revisao_formatted = [format_asset(r) for r in em_revisao_raw]

    time_formatted = data.timestamp.astimezone(timezone(timedelta(hours=-3))).strftime(
        "%d/%m/%Y %H:%M:%S BRT"
    )

    dispersion_pct = None
    neutral_count = None
    if (
        data.total_count
        and data.up_count is not None
        and data.down_count is not None
        and data.total_count > 0
    ):
        dispersion_pct = (
            (data.up_count / (data.up_count + data.down_count)) * 100
            if (data.up_count + data.down_count) > 0
            else 0
        )
        neutral_count = max(0, data.total_count - (data.up_count + data.down_count))

    pregao_str = getattr(data, "pregao_data", None)
    if pregao_str:
        titulo_altas = f"Maiores altas · pregão {pregao_str}"
        titulo_baixas = f"Maiores baixas · pregão {pregao_str}"
    else:
        titulo_altas = "Maiores altas"
        titulo_baixas = "Maiores baixas"

    return {
        "highs": highs_formatted,
        "lows": lows_formatted,
        "time": time_formatted,
        "fonte": getattr(data, "fonte", "yfinance"),
        "up_count": data.up_count,
        "down_count": data.down_count,
        "total_count": data.total_count,
        "neutral_count": neutral_count,
        "dispersion_pct": dispersion_pct,
        "em_revisao": em_revisao_formatted,
        "titulo_altas": titulo_altas,
        "titulo_baixas": titulo_baixas,
        "pregao_data": pregao_str,
        "pregao": pregao_str,
        "ausentes_count": getattr(data, "ausentes_count", 0),
        "ausentes_tickers": ausentes_tickers,
        "media_simples_pct": getattr(data, "media_simples_pct", None),
        "media_simples_n": getattr(data, "media_simples_n", None),
    }


# Spec 196: a ação média do dia contra o Ibovespa.
MENOS = "−"  # sinal de menos tipográfico
LIMIAR_LEITURA_PP = 0.50
JANELA_MESMA_RODADA = timedelta(minutes=20)
LEITURA_INDICE_ALEM = "o índice foi além da ação média"
LEITURA_MEDIA_ALEM = "a ação média foi além do índice"
LEITURA_JUNTOS = "índice e ação média andaram juntos"


def _com_sinal(valor: float) -> str:
    """`0.3` -> `+0,30`; `-0.7` -> `−0,70`; zero sem sinal."""
    texto = f"{abs(valor):.2f}".replace(".", ",")
    if round(valor, 2) > 0:
        return "+" + texto
    if round(valor, 2) < 0:
        return MENOS + texto
    return texto


def leitura_da_diferenca(diferenca_pp: float) -> str:
    """Uma das três frases fixas da spec 196, pelo limiar de 0,50 p.p."""
    d = round(diferenca_pp, 9)
    if d <= -LIMIAR_LEITURA_PP:
        return LEITURA_INDICE_ALEM
    if d >= LIMIAR_LEITURA_PP:
        return LEITURA_MEDIA_ALEM
    return LEITURA_JUNTOS


def comparar_com_ibovespa(
    media_pct: float | None,
    n: int | None,
    ibov_pct: float | None,
    ibov_ts: datetime | None,
    media_ts: datetime | None,
    ibov_valida: bool,
) -> dict[str, Any] | None:
    """A ação média contra o Ibovespa da mesma rodada (spec 196).

    Percentuais entram em percentual (`0.30` é +0,30%); a diferença sai em
    pontos percentuais. Sem média, devolve None. A comparação só vale com o
    Ibovespa válido (variação disponível e fora de revisão) e as duas coletas a
    no máximo 20 minutos uma da outra; fora disso, só a média.
    """
    if media_pct is None or not n:
        return None
    comparavel = (
        ibov_valida
        and ibov_pct is not None
        and ibov_ts is not None
        and media_ts is not None
        and abs(ibov_ts - media_ts) <= JANELA_MESMA_RODADA
    )
    resultado: dict[str, Any] = {
        "media_pct": media_pct,
        "amostra": n,
        "ibovespa_pct": None,
        "diferenca_pp": None,
        "leitura": None,
        "media_fmt": _com_sinal(media_pct) + "%",
        "ibovespa_fmt": None,
        "diferenca_fmt": None,
    }
    if comparavel:
        assert ibov_pct is not None
        diferenca = media_pct - ibov_pct
        resultado.update(
            {
                "ibovespa_pct": ibov_pct,
                "diferenca_pp": diferenca,
                "leitura": leitura_da_diferenca(diferenca),
                "ibovespa_fmt": _com_sinal(ibov_pct) + "%",
                "diferenca_fmt": _com_sinal(diferenca) + " p.p.",
            }
        )
    return resultado


def acao_media_api(comparacao: dict[str, Any] | None) -> dict[str, Any] | None:
    """A chave `acao_media` do `/api/snapshot`: só os números e a leitura."""
    if comparacao is None:
        return None
    chaves = ("media_pct", "amostra", "ibovespa_pct", "diferenca_pp", "leitura")
    return {k: comparacao[k] for k in chaves}
