import json
import logging
import sys
from datetime import datetime, timezone

import httpx

from app.collectors import mt5
from app.collectors.highlights import TICKERS
from app.collectors.utils import fetch_with_retry
from app.database import ExaustaoTendenciaData, save_exaustao_tendencia_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fetch_yfinance() -> ExaustaoTendenciaData | None:
    parsed_results = []
    successful_fetches = 0
    batch_size = 15
    batches = [TICKERS[i : i + batch_size] for i in range(0, len(TICKERS), batch_size)]

    with httpx.Client(timeout=10.0) as client:
        for batch in batches:
            symbols = ",".join([f"{t}.SA" for t in batch])
            url = f"https://query1.finance.yahoo.com/v7/finance/spark?symbols={symbols}&range=10d&interval=1d"
            try:
                response = fetch_with_retry(url, client=client)
                data = response.json()
                for item in data.get("spark", {}).get("result", []):
                    if not item.get("response"):
                        continue
                    symbol = item.get("symbol", "").replace(".SA", "")
                    try:
                        closes = item["response"][0]["indicators"]["quote"][0]["close"]
                        volumes = item["response"][0]["indicators"]["quote"][0][
                            "volume"
                        ]
                    except (KeyError, IndexError):
                        continue

                    if len(closes) != len(volumes):
                        continue

                    valid_data = [
                        (c, v)
                        for c, v in zip(closes, volumes)
                        if c is not None and v is not None
                    ]

                    if len(valid_data) < 2:
                        continue

                    dias = 0
                    cum_return = 0.0
                    for i in range(len(valid_data) - 1, 0, -1):
                        curr_c, curr_v = valid_data[i]
                        prev_c, prev_v = valid_data[i - 1]
                        if curr_c > prev_c and curr_v < prev_v:
                            dias += 1
                        else:
                            break

                    if dias >= 3:
                        last_price = valid_data[-1][0]
                        start_price = valid_data[-(dias + 1)][0]
                        cum_return = ((last_price - start_price) / start_price) * 100
                        parsed_results.append(
                            {
                                "ticker": symbol,
                                "dias_consecutivos": dias,
                                "variacao_acumulada": cum_return,
                            }
                        )
                successful_fetches += 1
            except httpx.HTTPError as e:
                logger.error(f"Error fetching batch {symbols} from yfinance: {e}")
                continue

    if successful_fetches == 0:
        return None

    parsed_results.sort(
        key=lambda x: (x["dias_consecutivos"], -x["variacao_acumulada"]), reverse=True
    )
    top_alerts = parsed_results[:3]
    return ExaustaoTendenciaData(
        timestamp=datetime.now(timezone.utc),
        alertas_json=json.dumps(top_alerts),
        fonte=mt5.fonte_efetiva("yfinance"),
    )


def collect_and_save() -> bool:
    logger.info("Starting exaustao tendencia collection...")
    data = fetch_yfinance()
    if data:
        save_exaustao_tendencia_data(data)
        logger.info("Saved exaustao tendencia data.")
        return True
    logger.info("No exaustao tendencia data found or failed to collect.")
    return False


if __name__ == "__main__":
    if not collect_and_save():
        sys.exit(1)
