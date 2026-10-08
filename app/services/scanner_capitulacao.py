import json
from datetime import timezone, timedelta
from dataclasses import dataclass
from app.database import get_latest_scanner_capitulacao_data


@dataclass
class ScannerCapitulacaoView:
    fonte: str
    time: str
    alertas: list[dict]


def get_scanner_capitulacao_view() -> ScannerCapitulacaoView | None:
    data = get_latest_scanner_capitulacao_data()
    if not data:
        return None
    return ScannerCapitulacaoView(
        fonte=data.fonte,
        time=data.timestamp.astimezone(timezone(timedelta(hours=-3))).strftime(
            "%d/%m/%Y %H:%M:%S BRT"
        ),
        alertas=json.loads(data.alertas_json),
    )
