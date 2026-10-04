from app.database import get_latest_apetite_risco_data


def get_apetite_risco_view_data():
    data = get_latest_apetite_risco_data()
    if not data:
        return None
    return {
        "time": data.timestamp.strftime("%H:%M"),
        "fonte": data.fonte,
        "estado": data.estado,
        "diferenca": data.diferenca,
    }
