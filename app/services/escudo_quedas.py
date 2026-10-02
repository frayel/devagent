import json
from dataclasses import dataclass
from datetime import datetime, timezone
from app.database import get_latest_escudo_quedas_data


@dataclass
class EscudoQuedasViewData:
    timestamp: datetime
    time: str
    fonte: str
    qtd_quedas_ibov: int
    top3: list[dict]


def get_escudo_quedas_view_data() -> EscudoQuedasViewData | None:
    data = get_latest_escudo_quedas_data()
    if not data:
        return None

    try:
        parsed_data = json.loads(data.top3_json)
        local_time = data.timestamp.astimezone(timezone.utc)
        return EscudoQuedasViewData(
            timestamp=local_time,
            time=local_time.strftime("%H:%M"),
            fonte=data.fonte,
            qtd_quedas_ibov=parsed_data.get("qtd_quedas_ibov", 0),
            top3=parsed_data.get("top3", []),
        )
    except Exception:
        return None
