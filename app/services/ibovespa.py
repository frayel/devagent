from typing import Any

from app.database import get_latest_ibovespa_data


def get_ibovespa_view_data() -> dict[str, Any] | None:
    data = get_latest_ibovespa_data()
    if not data:
        return None

    variation = data.current_price - data.previous_close
    variation_percent = (
        (variation / data.previous_close) * 100 if data.previous_close else 0.0
    )

    is_positive = variation > 0
    is_negative = variation < 0

    # format strings for view
    current_formatted = f"{int(data.current_price):,}".replace(",", ".")
    variation_formatted = f"{int(variation):,}".replace(",", ".")
    variation_percent_formatted = f"{variation_percent:.2f}%"

    if variation > 0:
        variation_formatted = f"+{variation_formatted}"
        variation_percent_formatted = f"+{variation_percent_formatted}"

    # convert timestamp to local display
    time_formatted = data.timestamp.strftime("%d/%m/%Y %H:%M:%S UTC")

    return {
        "current_price": current_formatted,
        "variation": variation_formatted,
        "variation_percent": variation_percent_formatted,
        "is_positive": is_positive,
        "is_negative": is_negative,
        "time": time_formatted,
        "history_json": data.history_json,
    }
