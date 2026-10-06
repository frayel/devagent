from app.database import get_latest_volatilidade_silenciosa_data
import json


def get_volatilidade_silenciosa_view() -> dict:
    data = get_latest_volatilidade_silenciosa_data()
    if data:
        try:
            alertas = json.loads(data.alertas_json)
        except Exception:
            alertas = []
        return {
            "coletado_em": data.timestamp.isoformat(),
            "fonte": data.fonte,
            "alertas": alertas,
        }
    return {}
