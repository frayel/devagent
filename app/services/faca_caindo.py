from datetime import timezone, timedelta
from dataclasses import dataclass
import json
import logging

from app.database import get_latest_faca_caindo_data

logger = logging.getLogger(__name__)


@dataclass
class AlertaFacaCaindo:
    """Uma ação em sequência de quedas, como o coletor grava em `alertas_json`."""

    ticker: str
    dias: int
    variacao_acumulada: float


@dataclass
class FacaCaindoView:
    fonte: str
    time: str
    alertas: list[AlertaFacaCaindo]


def _alertas(alertas_json: str) -> list[AlertaFacaCaindo]:
    alertas = []
    for item in json.loads(alertas_json):
        try:
            alertas.append(
                AlertaFacaCaindo(
                    ticker=str(item["ticker"]),
                    dias=int(item["dias"]),
                    variacao_acumulada=float(item["variacao_acumulada"]),
                )
            )
        except (KeyError, TypeError, ValueError):
            # Um alerta malformado sai do painel; o resto continua visível.
            logger.warning("Alerta de faca caindo descartado: %r", item)
    return alertas


def get_faca_caindo_view() -> FacaCaindoView | None:
    data = get_latest_faca_caindo_data()
    if not data:
        return None
    return FacaCaindoView(
        fonte=data.fonte,
        time=data.timestamp.astimezone(timezone(timedelta(hours=-3))).strftime(
            "%d/%m/%Y %H:%M:%S BRT"
        ),
        alertas=_alertas(data.alertas_json),
    )
