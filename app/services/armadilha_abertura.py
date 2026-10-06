import json
from datetime import timezone, timedelta
from app.database import get_latest_armadilha_abertura_data


def get_armadilha_abertura_view():
    data = get_latest_armadilha_abertura_data()
    if not data:
        return None

    try:
        alertas = json.loads(data.alertas_json)
    except Exception:
        alertas = []

    brt = timezone(timedelta(hours=-3))
    return {
        "alertas": alertas,
        "fonte": getattr(data, "fonte", "yfinance"),
        "time": data.timestamp.astimezone(brt).strftime("%d/%m/%Y %H:%M:%S BRT"),
    }
