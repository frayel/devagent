from datetime import timezone, timedelta
from app.database import get_latest_rotacao_capital_data


def get_rotacao_capital_view() -> dict | None:
    data = get_latest_rotacao_capital_data()
    if not data:
        return None
    return {
        "estado": data.estado,
        "var_bancos": data.var_bancos,
        "var_commodities": data.var_commodities,
        # Bancos menos commodities, em p.p.: o eixo do gauge divergente (spec 026).
        "diferenca": (data.var_bancos - data.var_commodities)
        if data.var_bancos is not None and data.var_commodities is not None
        else None,
        "time": data.timestamp.astimezone(timezone(timedelta(hours=-3))).strftime(
            "%d/%m/%Y %H:%M:%S BRT"
        ),
        "coletado_em": data.timestamp,
        "fonte": data.fonte,
    }
