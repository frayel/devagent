import json
import logging
import sys
from datetime import datetime, timezone

import httpx

from app.database import VolumeAlertsData, save_volume_alerts_data
from app.collectors.utils import fetch_with_retry
from app.collectors.highlights import TICKERS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fetch_yfinance() -> VolumeAlertsData | None:
    parsed_results = []
    successful_fetches = 0

    batch_size = 15
    batches = [TICKERS[i : i + batch_size] for i in range(0, len(TICKERS), batch_size)]

    with httpx.Client(timeout=10.0) as client:
        for batch in batches:
            symbols = ",".join([f"{t}.SA" for t in batch])
            # Fetch 1 month of daily data to get ~21 trading sessions
            url = f"https://query1.finance.yahoo.com/v7/finance/spark?symbols={symbols}&range=1mo&interval=1d"
            try:
                response = fetch_with_retry(url, client=client)
                data = response.json()
                successful_fetches += 1

                for item in data.get("spark", {}).get("result", []):
                    if not item.get("response"):
                        continue

                    symbol = item.get("symbol", "").replace(".SA", "")

                    try:
                        timestamp = item["response"][0]["timestamp"]
                        volumes = item["response"][0]["indicators"]["quote"][0][
                            "volume"
                        ]
                    except KeyError:
                        continue

                    # Filter out any None values for valid trading sessions
                    valid_history = [
                        (t, v) for t, v in zip(timestamp, volumes) if v is not None
                    ]

                    if len(valid_history) < 2:
                        continue

                    # The last session is the current one (today)
                    last_volume = valid_history[-1][1]

                    # Get previous sessions for the moving average (up to 21)
                    previous_sessions = valid_history[:-1][-21:]

                    if not previous_sessions:
                        continue

                    previous_volumes = [s[1] for s in previous_sessions]
                    avg_volume = sum(previous_volumes) / len(previous_volumes)

                    if avg_volume == 0:
                        continue

                    ratio = last_volume / avg_volume

                    if ratio > 1.5:
                        meta = item["response"][0].get("meta", {})
                        price = meta.get("regularMarketPrice", 0.0)

                        parsed_results.append(
                            {
                                "ticker": symbol,
                                "ratio": ratio,
                                "price": price,
                            }
                        )

            except httpx.HTTPError as e:
                logger.error(f"Error fetching batch {symbols} from yfinance: {e}")
                continue

    if successful_fetches == 0:
        return None

    # Sort by ratio descending
    parsed_results.sort(key=lambda x: x["ratio"], reverse=True)

    # Get top 5
    top_alerts = parsed_results[:5]

    return VolumeAlertsData(
        timestamp=datetime.now(timezone.utc),
        alerts_json=json.dumps(top_alerts),
        fonte="yfinance",
    )


def collect_and_save() -> bool:
    logger.info("Starting volume alerts collection...")
    data = fetch_yfinance()

    if data:
        save_volume_alerts_data(data)
        logger.info("Saved volume alerts data.")
        return True
    else:
        logger.info("No volume alerts found or failed to collect data.")
        return False


if __name__ == "__main__":
    success = collect_and_save()
    if not success:
        sys.exit(1)
