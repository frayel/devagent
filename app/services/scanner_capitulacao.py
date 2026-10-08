import json
from datetime import timedelta, timezone
from app.database import get_latest_scanner_capitulacao_data


def view_model() -> dict | None:
    data = get_latest_scanner_capitulacao_data()
    if not data:
        return None

    return {
        "alertas": json.loads(data.alertas_json),
        "time": data.timestamp.astimezone(timezone(timedelta(hours=-3))).strftime(
            "%d/%m/%Y %H:%M:%S BRT"
        ),
        "fonte": data.fonte,
    }
