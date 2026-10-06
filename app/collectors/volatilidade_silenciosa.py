import json
import logging
import sys
from datetime import datetime, timezone

import httpx

from app.database import VolatilidadeSilenciosaData, save_volatilidade_silenciosa_data
from app.collectors import mt5
from app.collectors.utils import fetch_with_retry
from app.collectors.highlights import TICKERS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fetch_yfinance() -> VolatilidadeSilenciosaData | None:
    parsed_results: list[dict] = []
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
                successful_fetches += 1

                for item in data.get("spark", {}).get("result", []):
                    if not item.get("response") or not item.get("symbol"):
                        continue

                    symbol = item.get("symbol", "").replace(".SA", "")

                    # Check if symbol was already processed
                    if any(a["ticker"] == symbol for a in parsed_results):
                        continue

                    symbol = item.get("symbol", "").replace(".SA", "")

                    try:
                        quote = item["response"][0]["indicators"]["quote"][0]
                        open_price = quote["open"][0]
                        high_price = quote["high"][0]
                        low_price = quote["low"][0]
                        close_price = quote["close"][0]
                    except (KeyError, IndexError):
                        continue

                    if (
                        open_price is None
                        or high_price is None
                        or low_price is None
                        or close_price is None
                        or open_price == 0
                        or low_price == 0
                    ):
                        continue

                    amplitude = ((high_price - low_price) / low_price) * 100
                    variacao = ((close_price - open_price) / open_price) * 100

                    if abs(variacao) <= 0.5:
                        parsed_results.append(
                            {
                                "ticker": symbol,
                                "amplitude": amplitude,
                                "variacao": variacao,
                            }
                        )
            except httpx.HTTPError as e:
                logger.error(f"Error fetching batch {symbols} from yfinance: {e}")
                continue

    if successful_fetches == 0:
        return None

    # Sort by amplitude descending
    parsed_results.sort(key=lambda x: x["amplitude"], reverse=True)

    # Get top 3
    top_alerts = parsed_results[:3]

    return VolatilidadeSilenciosaData(
        timestamp=datetime.now(timezone.utc),
        alertas_json=json.dumps(top_alerts),
        fonte=mt5.fonte_efetiva("yfinance"),
    )


def collect_and_save() -> bool:
    logger.info("Starting volatilidade silenciosa collection...")
    data = fetch_yfinance()

    if data:
        save_volatilidade_silenciosa_data(data)
        logger.info("Saved volatilidade silenciosa data.")
        return True
    else:
        logger.info("No volatilidade silenciosa data found or failed to collect.")
        return False


if __name__ == "__main__":
    success = collect_and_save()
    if not success:
        sys.exit(1)
