from app.database import get_latest_radar_anomalia_fechamento_data
from datetime import timezone, timedelta
import json


def get_radar_anomalia_fechamento_view() -> dict:
    data = get_latest_radar_anomalia_fechamento_data()
    if data:
        try:
            alertas = json.loads(data.alertas_json)
        except Exception:
            alertas = []
        return {
            "coletado_em": data.timestamp.astimezone(
                timezone(timedelta(hours=-3))
            ).strftime("%d/%m/%Y %H:%M:%S BRT"),
            "fonte": data.fonte,
            "alertas": alertas,
        }
    return {}
