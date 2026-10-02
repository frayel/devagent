import json
from typing import Any
from datetime import timezone, timedelta
from app.database import get_latest_dolar_correlation_data


def get_dolar_correlation_view_data() -> dict[str, Any] | None:
    data = get_latest_dolar_correlation_data()
    if not data:
        return None

    try:
        positivas = json.loads(data.positivas_json)
        negativas = json.loads(data.negativas_json)
    except json.JSONDecodeError:
        return None

    def format_corr(c):
        return f"{c:.2f}".replace(".", ",")

    pos_formatted = [
        {
            "ticker": item["ticker"],
            "correlation": item["correlation"],
            "correlation_formatted": format_corr(item["correlation"]),
        }
        for item in positivas
    ]
    neg_formatted = [
        {
            "ticker": item["ticker"],
            "correlation": item["correlation"],
            "correlation_formatted": format_corr(item["correlation"]),
        }
        for item in negativas
    ]

    return {
        "positivas": pos_formatted,
        "negativas": neg_formatted,
        "time": data.timestamp.astimezone(timezone(timedelta(hours=-3))).strftime(
            "%d/%m/%Y %H:%M:%S BRT"
        ),
        "fonte": getattr(data, "fonte", "yfinance"),
    }
