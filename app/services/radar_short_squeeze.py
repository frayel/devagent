import json
from datetime import timezone, timedelta
from app.database import get_latest_radar_short_squeeze_data


def get_radar_short_squeeze_view() -> dict | None:
    data = get_latest_radar_short_squeeze_data()
    if not data:
        return None

    try:
        alertas = json.loads(data.alertas_json)
    except Exception:
        alertas = []

    dt_brt = data.timestamp.astimezone(timezone(timedelta(hours=-3)))

    return {
        "coletado_em": dt_brt.strftime("%d/%m/%Y %H:%M:%S BRT"),
        "fonte": data.fonte,
        "alertas": alertas,
    }
