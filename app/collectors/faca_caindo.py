import json
import logging
import sys
from datetime import datetime, timezone

import httpx

from app.database import FacaCaindoData, save_faca_caindo_data
from app.collectors import mt5
from app.collectors.utils import fetch_with_retry
from app.collectors.highlights import TICKERS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fetch_yfinance() -> FacaCaindoData | None:
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
                    except (KeyError, IndexError):
                        continue

                    valid_closes = [v for v in closes if v is not None]

                    if len(valid_closes) < 2:
                        continue

                    drops = 0
                    cum_return = 0.0
                    for i in range(len(valid_closes) - 1, 0, -1):
                        if valid_closes[i] < valid_closes[i - 1]:
                            drops += 1
                        else:
                            break
                    if drops >= 3:
                        last_price = valid_closes[-1]
                        start_drop_price = valid_closes[-(drops + 1)]
                        cum_return = (
                            (last_price - start_drop_price) / start_drop_price
                        ) * 100
                        parsed_results.append(
                            {
                                "ticker": symbol,
                                "dias": drops,
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
        key=lambda x: (x["dias"], -x["variacao_acumulada"]), reverse=True
    )
    top_alerts = parsed_results[:3]
    return FacaCaindoData(
        timestamp=datetime.now(timezone.utc),
        alertas_json=json.dumps(top_alerts),
        fonte=mt5.fonte_efetiva("yfinance"),
    )


def collect_and_save() -> bool:
    logger.info("Starting faca caindo collection...")
    data = fetch_yfinance()
    if data:
        save_faca_caindo_data(data)
        logger.info("Saved faca caindo data.")
        return True
    logger.info("No faca caindo data found or failed to collect.")
    return False


if __name__ == "__main__":
    if not collect_and_save():
        sys.exit(1)
