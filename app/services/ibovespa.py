from typing import Any
import json

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
    variation_percent_formatted = f"{variation_percent:.2f}%".replace(".", ",")

    if variation > 0:
        variation_formatted = f"+{variation_formatted}"
        variation_percent_formatted = f"+{variation_percent_formatted}"

    # calculate moving averages formatting and signals
    mm21_formatted = None
    mm21_signal = None
    if data.mm21 is not None:
        mm21_formatted = f"{int(data.mm21):,}".replace(",", ".")
        if data.current_price > data.mm21:
            mm21_signal = "Alta"
        elif data.current_price < data.mm21:
            mm21_signal = "Baixa"
        else:
            mm21_signal = "Neutra"

    mm200_formatted = None
    mm200_signal = None
    if data.mm200 is not None:
        mm200_formatted = f"{int(data.mm200):,}".replace(",", ".")
        if data.current_price > data.mm200:
            mm200_signal = "Alta"
        elif data.current_price < data.mm200:
            mm200_signal = "Baixa"
        else:
            mm200_signal = "Neutra"

    # convert timestamp to local display
    time_formatted = data.timestamp.strftime("%d/%m/%Y %H:%M:%S UTC")

    history_dict = {}
    if data.history_json:
        try:
            history_dict = json.loads(data.history_json)
        except json.JSONDecodeError:
            pass

    return {
        "current_price": current_formatted,
        "variation": variation_formatted,
        "variation_percent": variation_percent_formatted,
        "is_positive": is_positive,
        "is_negative": is_negative,
        "time": time_formatted,
        "history_dict": history_dict,
        "fonte": data.fonte,
        "mm21": mm21_formatted,
        "mm21_signal": mm21_signal,
        "mm200": mm200_formatted,
        "mm200_signal": mm200_signal,
    }
