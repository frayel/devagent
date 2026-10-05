import json
from app.database import get_latest_sobrevivencia_semanal_data


def get_sobrevivencia_semanal_view() -> dict | None:
    data = get_latest_sobrevivencia_semanal_data()
    if not data:
        return None

    try:
        alertas = json.loads(data.alertas_json)
    except Exception:
        alertas = []

    return {
        "time": data.timestamp.strftime("%d/%m/%Y %H:%M"),
        "fonte": data.fonte,
        "alertas": alertas,
    }
