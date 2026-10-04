import json
import logging
import sys
from datetime import datetime, timezone

import httpx

from app.database import VariacaoSubitaData, save_variacao_subita_data
from app.collectors.utils import fetch_with_retry
from app.collectors.highlights import TICKERS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fetch_yfinance() -> VariacaoSubitaData | None:
    parsed_results = []
    successful_fetches = 0

    batch_size = 15
    batches = [TICKERS[i : i + batch_size] for i in range(0, len(TICKERS), batch_size)]

    with httpx.Client(timeout=10.0) as client:
        for batch in batches:
            symbols = ",".join([f"{t}.SA" for t in batch])
            # Fetch 1 day of 15-minute interval data
            url = f"https://query1.finance.yahoo.com/v7/finance/spark?symbols={symbols}&range=1d&interval=15m"
            try:
                response = fetch_with_retry(url, client=client)
                data = response.json()
                successful_fetches += 1

                for item in data.get("spark", {}).get("result", []):
                    if not item.get("response"):
                        continue

                    symbol = item.get("symbol", "").replace(".SA", "")

                    try:
                        closes = item["response"][0]["indicators"]["quote"][0]["close"]
                    except (KeyError, IndexError):
                        continue

                    # Filter out any None values
                    valid_closes = [v for v in closes if v is not None]

                    if len(valid_closes) < 5:
                        continue

                    # 4 intervals of 15m = 1 hour
                    last_price = valid_closes[-1]
                    price_1h_ago = valid_closes[-5]

                    if price_1h_ago == 0:
                        continue

                    change_percent = ((last_price - price_1h_ago) / price_1h_ago) * 100

                    if abs(change_percent) > 1.5:
                        parsed_results.append(
                            {
                                "ticker": symbol,
                                "change_percent": change_percent,
                            }
                        )

            except httpx.HTTPError as e:
                logger.error(f"Error fetching batch {symbols} from yfinance: {e}")
                continue

    if successful_fetches == 0:
        return None

    # Sort by absolute change descending
    parsed_results.sort(key=lambda x: abs(x["change_percent"]), reverse=True)

    # Get top 3
    top_alerts = parsed_results[:3]

    return VariacaoSubitaData(
        timestamp=datetime.now(timezone.utc),
        alertas_json=json.dumps(top_alerts),
        fonte="yfinance",
    )


def collect_and_save() -> bool:
    logger.info("Starting variacao subita collection...")
    data = fetch_yfinance()

    if data:
        save_variacao_subita_data(data)
        logger.info("Saved variacao subita data.")
        return True
    else:
        logger.info("No variacao subita data found or failed to collect.")
        return False


if __name__ == "__main__":
    success = collect_and_save()
    if not success:
        sys.exit(1)
