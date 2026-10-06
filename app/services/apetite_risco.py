from datetime import timezone, timedelta
from app.database import get_latest_apetite_risco_data


def get_apetite_risco_view_data():
    data = get_latest_apetite_risco_data()
    if not data:
        return None
    return {
        "time": data.timestamp.astimezone(timezone(timedelta(hours=-3))).strftime(
            "%d/%m/%Y %H:%M:%S BRT"
        ),
        "fonte": data.fonte,
        "estado": data.estado,
        "diferenca": data.diferenca,
    }
