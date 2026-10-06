import json
from dataclasses import dataclass
from typing import Any
from datetime import timezone, timedelta
from app.database import get_latest_atrasadas_rally_data


@dataclass
class AtrasadasRallyViewData:
    time: str
    fonte: str
    rally_valido: bool
    top3: list[dict[str, Any]]


def get_atrasadas_rally_view_data() -> AtrasadasRallyViewData | None:
    data = get_latest_atrasadas_rally_data()
    if not data:
        return None

    try:
        top3 = json.loads(data.top3_json)
    except json.JSONDecodeError:
        top3 = []

    return AtrasadasRallyViewData(
        time=data.timestamp.astimezone(timezone(timedelta(hours=-3))).strftime(
            "%d/%m/%Y %H:%M:%S BRT"
        ),
        fonte=data.fonte,
        rally_valido=data.rally_valido,
        top3=top3,
    )
