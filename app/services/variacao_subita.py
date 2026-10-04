import json
from datetime import timedelta, timezone

from app.database import get_latest_variacao_subita_data


def get_variacao_subita_view_data() -> dict | None:
    data = get_latest_variacao_subita_data()
    if not data:
        return None

    try:
        alertas = json.loads(data.alertas_json)
    except json.JSONDecodeError:
        alertas = []

    brt = timezone(timedelta(hours=-3))
    time_str = data.timestamp.astimezone(brt).strftime("%H:%M")

    return {
        "time": time_str,
        "fonte": data.fonte,
        "alertas": alertas,
    }
