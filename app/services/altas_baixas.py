import json
from typing import Any

from app.database import get_latest_altas_baixas_data


def format_ticker_data(item: dict[str, Any]) -> dict[str, Any]:
    ticker = item["ticker"]
    if ticker.endswith(".SA"):
        ticker = ticker[:-3]

    price_formatted = f"{item['price']:.2f}".replace(".", ",")
    variation_percent = item["variation_percent"]
    variation_percent_formatted = f"{variation_percent:.2f}%"

    if variation_percent > 0:
        variation_percent_formatted = f"+{variation_percent_formatted}"

    return {
        "ticker": ticker,
        "price": price_formatted,
        "variation_percent": variation_percent_formatted,
        "is_positive": variation_percent > 0,
        "is_negative": variation_percent < 0,
    }


def get_altas_baixas_view_data() -> dict[str, Any] | None:
    data = get_latest_altas_baixas_data()
    if not data:
        return None

    top_altas = json.loads(data.top_altas_json)
    top_baixas = json.loads(data.top_baixas_json)

    top_altas_formatted = [format_ticker_data(item) for item in top_altas]
    top_baixas_formatted = [format_ticker_data(item) for item in top_baixas]

    time_formatted = data.timestamp.strftime("%d/%m/%Y %H:%M:%S UTC")

    return {
        "top_altas": top_altas_formatted,
        "top_baixas": top_baixas_formatted,
        "time": time_formatted,
        "source": data.source,
    }
