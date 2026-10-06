from typing import Any
from datetime import timezone, timedelta

from app.database import get_latest_coesao_data


def get_coesao_view_data() -> dict[str, Any] | None:
    data = get_latest_coesao_data()
    if not data:
        return None

    time_formatted = data.timestamp.astimezone(timezone(timedelta(hours=-3))).strftime(
        "%d/%m/%Y %H:%M:%S BRT"
    )

    estado = "Neutra"
    if data.concordantes >= 7:
        estado = "Alta Coesão"
    elif data.concordantes <= 3:
        estado = "Distorção"

    return {
        "concordantes": data.concordantes,
        "total": data.total,
        "proporcao": f"{data.concordantes} de {data.total} ações",
        "estado": estado,
        # Cor do gauge (spec 026): alta de 7 em diante, baixa até 3.
        "cor": "alta"
        if data.concordantes >= 7
        else "baixa"
        if data.concordantes <= 3
        else "neutra",
        "time": time_formatted,
        "fonte": data.fonte,
    }
