from dataclasses import dataclass
import json
from app.database import get_latest_compradores_fundo_data


@dataclass
class CompradoresFundoView:
    fonte: str
    time: str
    alertas: list[dict]


def get_compradores_fundo_view() -> CompradoresFundoView | None:
    data = get_latest_compradores_fundo_data()
    if not data:
        return None
    return CompradoresFundoView(
        fonte=data.fonte,
        time=data.timestamp.strftime("%H:%M"),
        alertas=json.loads(data.alertas_json),
    )
