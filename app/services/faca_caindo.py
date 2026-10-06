from datetime import timezone, timedelta
from dataclasses import dataclass
import json
from app.database import get_latest_faca_caindo_data


@dataclass
class FacaCaindoView:
    fonte: str
    time: str
    alertas: list[dict]


def get_faca_caindo_view() -> FacaCaindoView | None:
    data = get_latest_faca_caindo_data()
    if not data:
        return None
    return FacaCaindoView(
        fonte=data.fonte,
        time=data.timestamp.astimezone(timezone(timedelta(hours=-3))).strftime(
            "%d/%m/%Y %H:%M:%S BRT"
        ),
        alertas=json.loads(data.alertas_json),
    )
