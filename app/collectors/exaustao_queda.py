import json
import logging
import sys
from datetime import datetime, timezone, timedelta

import httpx

from app.collectors import mt5
from app.collectors.highlights import TICKERS
from app.collectors.utils import fetch_historico_diario_yfinance_spark
from app.database import ExaustaoQuedaData, save_exaustao_queda_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _fracao_do_pregao(agora: datetime) -> float:
    # Abertura 10:00, Fechamento 18:00
    local = agora.astimezone(timezone(timedelta(hours=-3)))
    if local.hour < 10:
        return 0.1
    if local.hour >= 18:
        return 1.0

    minutos = (local.hour - 10) * 60 + local.minute
    total = 8 * 60
    return max(minutos / total, 0.1)


def fetch_yfinance() -> ExaustaoQuedaData | None:
    parsed_results = []
    successful_fetches = 0

    with httpx.Client(timeout=10.0) as client:
        try:
            results = fetch_historico_diario_yfinance_spark(
                TICKERS, "25d", "1d", client
            )
            for item in results:
                if not item.get("response"):
                    continue
                symbol = item.get("symbol", "").replace(".SA", "")
                try:
                    closes = item["response"][0]["indicators"]["quote"][0]["close"]
                    opens = item["response"][0]["indicators"]["quote"][0]["open"]
                    volumes = item["response"][0]["indicators"]["quote"][0]["volume"]
                except (KeyError, IndexError):
                    continue

                valid_data = [
                    (c, o, v)
                    for c, o, v in zip(closes, opens, volumes)
                    if c is not None and o is not None and v is not None
                ]

                if len(valid_data) < 22:
                    continue

                hoje = valid_data[-1]
                ontem = valid_data[-2]
                d2 = valid_data[-3]
                d3 = valid_data[-4]
                d4 = valid_data[-5]

                if not (ontem[0] < d2[0] and d2[0] < d3[0] and d3[0] < d4[0]):
                    continue

                queda_acumulada = (ontem[0] / d4[0]) - 1

                if hoje[1] >= ontem[0]:
                    continue

                if hoje[0] <= hoje[1]:
                    continue

                recuperacao_intraday = (hoje[0] / hoje[1]) - 1

                volumes_21d = [v for c, o, v in valid_data[-22:-1]]
                media_volume_21d = sum(volumes_21d) / len(volumes_21d)

                volume_projetado = hoje[2] / _fracao_do_pregao(
                    datetime.now(timezone.utc)
                )

                if volume_projetado <= media_volume_21d:
                    continue

                parsed_results.append(
                    {
                        "ticker": symbol,
                        "queda_acumulada": queda_acumulada * 100,
                        "recuperacao_intraday": recuperacao_intraday * 100,
                    }
                )
            successful_fetches += 1
        except httpx.HTTPError as e:
            logger.error(f"Error fetching from yfinance: {e}")

    if successful_fetches == 0:
        return None

    parsed_results.sort(key=lambda x: -x["recuperacao_intraday"])
    return ExaustaoQuedaData(
        timestamp=datetime.now(timezone.utc),
        alertas_json=json.dumps(parsed_results[:3]),
        fonte=mt5.fonte_efetiva("yfinance"),
    )


def collect_and_save() -> bool:
    logger.info("Starting exaustao queda collection...")
    data = fetch_yfinance()
    if data:
        save_exaustao_queda_data(data)
        logger.info("Saved exaustao queda data.")
        return True
    logger.info("No exaustao queda data found or failed to collect.")
    return False


if __name__ == "__main__":
    if not collect_and_save():
        sys.exit(1)
