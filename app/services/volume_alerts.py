import json
from typing import Any
from datetime import timezone, timedelta

from app.database import get_latest_volume_alerts_data


def get_volume_alerts_view_data() -> dict[str, Any] | None:
    data = get_latest_volume_alerts_data()
    if not data:
        return None

    try:
        alerts = json.loads(data.alerts_json)
    except json.JSONDecodeError:
        return None

    alerts_formatted = []
    for alert in alerts:
        ratio = alert.get("ratio", 0.0)
        # Ratio 1.5 means 50% more, so percent is (ratio - 1) * 100
        # However, to match spec "+250% do volume normal" if ratio is 2.5, we show ratio * 100
        # Or better, +250% means 3.5 ratio. Wait, "Ratio > 1.5 (50% a mais)".
        # If the spec says "+250%", it usually refers to ((ratio - 1) * 100)
        # Let's use `(ratio) * 100` as the spec says "+250% do volume normal" which usually implies 2.5x volume normal.
        percent_above = (ratio) * 100

        ratio_formatted = f"+{percent_above:.0f}%".replace(".", ",")

        price = alert.get("price", 0.0)
        price_formatted = (
            f"R$ {price:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )

        alerts_formatted.append(
            {
                "ticker": alert.get("ticker", ""),
                "ratio_formatted": ratio_formatted,
                "price_formatted": price_formatted,
            }
        )

    time_formatted = data.timestamp.astimezone(timezone(timedelta(hours=-3))).strftime(
        "%d/%m/%Y %H:%M:%S BRT"
    )

    return {
        "alerts": alerts_formatted,
        "time": time_formatted,
        "fonte": getattr(data, "fonte", "yfinance"),
    }
