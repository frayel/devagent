from datetime import timedelta, timezone
from app.database import get_latest_rotacao_capital_data


def get_rotacao_capital_view_data() -> dict | None:
    data = get_latest_rotacao_capital_data()
    if not data:
        return None

    brt = timezone(timedelta(hours=-3))
    time_str = data.timestamp.astimezone(brt).strftime("%H:%M")

    return {
        "time": time_str,
        "fonte": data.fonte,
        "estado": data.estado,
        "var_bancos": data.var_bancos,
        "var_commodities": data.var_commodities,
    }
