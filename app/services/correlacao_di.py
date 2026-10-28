from typing import Any
from datetime import timezone, timedelta
from app.database import get_latest_correlacao_di_data


def get_correlacao_di_view_data() -> dict[str, Any] | None:
    data = get_latest_correlacao_di_data()
    if not data:
        return None

    def status(corr):
        if corr <= -0.7:
            return "Correlacionado"
        elif corr >= -0.3:
            return "Descolado"
        else:
            return "Neutro"

    return {
        "correlacao_intradiaria": data.correlacao_intradiaria,
        "correlacao_5d": data.correlacao_5d,
        "status_intradiaria": status(data.correlacao_intradiaria),
        "status_5d": status(data.correlacao_5d),
        "time": data.timestamp.astimezone(timezone(timedelta(hours=-3))).strftime(
            "%d/%m/%Y %H:%M:%S BRT"
        ),
        "coletado_em": data.timestamp.isoformat(),
        "fonte": data.fonte,
    }
