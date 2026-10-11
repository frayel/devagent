import json
from typing import Any
from datetime import timezone, timedelta
from app.database import get_latest_sensibilidade_juros_data


def get_sensibilidade_juros_view_data() -> dict[str, Any] | None:
    data = get_latest_sensibilidade_juros_data()
    if not data:
        return None

    try:
        alertas = json.loads(data.alertas_json)
    except json.JSONDecodeError:
        return None

    def format_corr(c):
        return f"{c:.2f}".replace(".", ",")

    alertas_formatted = [
        {
            "ticker": item["ticker"],
            "correlation": item["correlation"],
            "correlation_formatted": format_corr(item["correlation"]),
        }
        for item in alertas
    ]

    return {
        "alertas": alertas_formatted,
        "time": data.timestamp.astimezone(timezone(timedelta(hours=-3))).strftime(
            "%d/%m/%Y %H:%M:%S BRT"
        ),
        "fonte": getattr(data, "fonte", "yfinance"),
    }
