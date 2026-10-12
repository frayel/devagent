import json
import logging
import sys
from datetime import datetime, timezone

import httpx

from app.database import LiquidezAberturaData, save_liquidez_abertura_data
from app.collectors import mt5
from app.collectors.utils import fetch_with_retry
from app.collectors.highlights import TICKERS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fetch_yfinance() -> LiquidezAberturaData | None:
    parsed_results = []
    successful_fetches = 0

    with httpx.Client(timeout=10.0) as client:
        for i, symbol in enumerate(TICKERS):
            yf_symbol = f"{symbol}.SA"
            subdomain = "query1" if i % 2 == 0 else "query2"
            url = f"https://{subdomain}.finance.yahoo.com/v8/finance/chart/{yf_symbol}?range=1mo&interval=1d"
            try:
                response = fetch_with_retry(url, client=client)
                data = response.json()
                successful_fetches += 1

                result_list = data.get("chart", {}).get("result", [])
                if not result_list:
                    continue

                for item in result_list:
                    try:
                        timestamp = item["timestamp"]
                        quote = item["indicators"]["quote"][0]
                        volumes = quote["volume"]
                        closes = quote["close"]
                    except KeyError:
                        continue

                    valid_history = [
                        (t, v, c)
                        for t, v, c in zip(timestamp, volumes, closes)
                        if v is not None and c is not None
                    ]

                    if len(valid_history) < 10:
                        continue

                    # Today's volume
                    last_volume = valid_history[-1][1]
                    last_close = valid_history[-1][2]
                    prev_close = valid_history[-2][2]

                    # Previous days volume average
                    prev_days = valid_history[:-1][-10:]
                    avg_volume = sum(day[1] for day in prev_days) / len(prev_days)

                    if avg_volume == 0 or last_volume == 0:
                        continue

                    ratio = last_volume / avg_volume

                    # Only alert if volume is surprisingly high for current time
                    if ratio > 0.5:
                        var_pct = ((last_close / prev_close) - 1) * 100
                        parsed_results.append(
                            {
                                "ticker": symbol,
                                "ratio": ratio,
                                "var_pct": var_pct,
                            }
                        )

            except httpx.HTTPError as e:
                logger.error(f"Error fetching {yf_symbol} from yfinance: {e}")
                continue

    if successful_fetches == 0:
        return None

    parsed_results.sort(key=lambda x: x["ratio"], reverse=True)
    top_alerts = parsed_results[:3]

    return LiquidezAberturaData(
        timestamp=datetime.now(timezone.utc),
        alertas_json=json.dumps(top_alerts),
        fonte=mt5.fonte_efetiva("yfinance"),
    )


def collect_and_save() -> bool:
    logger.info("Starting Radar de Liquidez de Abertura collection...")
    data = fetch_yfinance()

    if data:
        save_liquidez_abertura_data(data)
        logger.info("Saved liquidez abertura data.")
        return True
    else:
        logger.info("No liquidez abertura data found or failed to collect.")
        return False


if __name__ == "__main__":
    success = collect_and_save()
    if not success:
        sys.exit(1)
