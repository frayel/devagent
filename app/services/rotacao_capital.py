from app.database import get_latest_rotacao_capital_data


def get_rotacao_capital_view() -> dict | None:
    data = get_latest_rotacao_capital_data()
    if not data:
        return None
    return {
        "estado": data.estado,
        "var_bancos": data.var_bancos,
        "var_commodities": data.var_commodities,
        "coletado_em": data.timestamp,
        "fonte": data.fonte,
    }
