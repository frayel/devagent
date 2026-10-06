import json
import logging
import sys
from datetime import datetime, timezone

import httpx

from app.database import CompradoresFundoData, save_compradores_fundo_data
from app.collectors import mt5
from app.collectors.utils import fetch_with_retry
from app.collectors.highlights import TICKERS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fetch_yfinance() -> CompradoresFundoData | None:
    parsed_results = []
    successful_fetches = 0
    batch_size = 15
    batches = [TICKERS[i : i + batch_size] for i in range(0, len(TICKERS), batch_size)]

    with httpx.Client(timeout=10.0) as client:
        for batch in batches:
            symbols = ",".join([f"{t}.SA" for t in batch])
            url = f"https://query1.finance.yahoo.com/v7/finance/spark?symbols={symbols}&range=1d&interval=1d"
            try:
                response = fetch_with_retry(url, client=client)
                data = response.json()

                for item in data.get("spark", {}).get("result", []):
                    if not item.get("response"):
                        continue

                    symbol = item.get("symbol", "").replace(".SA", "")

                    try:
                        indicators = item["response"][0]["indicators"]["quote"][0]
                        open_price = indicators.get("open", [None])[0]
                        low_price = indicators.get("low", [None])[0]
                        close_price = indicators.get("close", [None])[0]
                    except (KeyError, IndexError):
                        continue

                    if open_price is None or low_price is None or close_price is None:
                        continue
                    if open_price == 0:
                        continue

                    drop_percent = ((open_price - low_price) / open_price) * 100

                    if drop_percent > 1.5 and close_price >= open_price:
                        parsed_results.append(
                            {
                                "ticker": symbol,
                                "queda_maxima": -drop_percent,
                                "preco_atual": close_price,
                            }
                        )
                successful_fetches += 1
            except httpx.HTTPError as e:
                logger.error(f"Error fetching batch {symbols} from yfinance: {e}")
                continue

    if successful_fetches == 0:
        return None

    parsed_results.sort(key=lambda x: x["queda_maxima"])
    top_alerts = parsed_results[:3]

    return CompradoresFundoData(
        timestamp=datetime.now(timezone.utc),
        alertas_json=json.dumps(top_alerts),
        fonte=mt5.fonte_efetiva("yfinance"),
    )


def collect_and_save() -> bool:
    logger.info("Starting compradores de fundo collection...")
    data = fetch_yfinance()
    if data:
        save_compradores_fundo_data(data)
        logger.info("Saved compradores de fundo data.")
        return True
    logger.info("No compradores de fundo data found or failed to collect.")
    return False


if __name__ == "__main__":
    if not collect_and_save():
        sys.exit(1)
