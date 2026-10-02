import json
from typing import Any
from datetime import timezone, timedelta

from app.database import get_latest_highlights_data


def format_asset(asset: dict[str, Any]) -> dict[str, Any]:
    price = asset.get("price", 0.0)
    change_percent = asset.get("change_percent", 0.0)

    price_formatted = (
        f"R$ {price:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    )

    change_formatted = f"{change_percent:.2f}%".replace(".", ",")
    if change_percent > 0:
        change_formatted = f"+{change_formatted}"

    return {
        "ticker": asset.get("ticker", ""),
        "price_formatted": price_formatted,
        "change_percent_formatted": change_formatted,
        "is_positive": change_percent > 0,
        "is_negative": change_percent < 0,
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

    highs_formatted = [format_asset(h) for h in highs]
    lows_formatted = [format_asset(low) for low in lows]

    time_formatted = data.timestamp.astimezone(timezone(timedelta(hours=-3))).strftime(
        "%d/%m/%Y %H:%M:%S BRT"
    )

    dispersion_pct = None
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

    return {
        "highs": highs_formatted,
        "lows": lows_formatted,
        "time": time_formatted,
        "fonte": getattr(data, "fonte", "brapi"),
        "up_count": data.up_count,
        "down_count": data.down_count,
        "total_count": data.total_count,
        "dispersion_pct": dispersion_pct,
    }
