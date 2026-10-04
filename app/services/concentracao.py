from app.database import get_latest_concentracao_data
import json


def get_concentracao_view_data():
    data = get_latest_concentracao_data()
    if not data:
        return None
    return {
        "time": data.timestamp.strftime("%H:%M"),
        "fonte": data.fonte,
        "resumo": json.loads(data.resumo_json),
        "top3": json.loads(data.top3_json),
    }
