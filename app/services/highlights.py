import json
from typing import Any
from datetime import timezone, timedelta

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
    }
