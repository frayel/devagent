import json
import logging
import sys
from datetime import datetime, timezone

import httpx

from app.database import HighlightsData, save_highlights_data
from app.collectors import mt5
from app.collectors.utils import fetch_with_retry

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# List of highly liquid B3 tickers
TICKERS = [
    "PETR4",
    "VALE3",
    "ITUB4",
    "BBDC4",
    "B3SA3",
    "ABEV3",
    "BBDC3",
    "RENT3",
    "WEGE3",
    "BBAS3",
    "ITSA4",
    "SUZB3",
    "BPAC11",
    "RADL3",
    "EQTL3",
    "CSAN3",
    "PRIO3",
    "RDOR3",
    "RAIL3",
    "SBSP3",
    "VIVT3",
    "CMIG4",
    "LREN3",
    "CPLE3",
    "UGPA3",
    "ENEV3",
    "TIMS3",
    "TOTS3",
    "EGIE3",
    "HAPV3",
]


def fetch_yfinance() -> HighlightsData | None:
    parsed_results = []
    up_count = 0
    down_count = 0

    # Batching tickers in groups of 15 to respect URL length and API limits
    batch_size = 15
    batches = [TICKERS[i : i + batch_size] for i in range(0, len(TICKERS), batch_size)]

    with httpx.Client(timeout=10.0) as client:
        for batch in batches:
            symbols = ",".join([f"{t}.SA" for t in batch])
            url = f"https://query1.finance.yahoo.com/v8/finance/spark?symbols={symbols}&range=15d&interval=1d"
            try:
                response = fetch_with_retry(url, client=client)
                data = response.json()

                for item in data.get("spark", {}).get("result", []):
                    if not item.get("response"):
                        continue

                    symbol = item.get("symbol", "").replace(".SA", "")
                    meta = item["response"][0].get("meta", {})
                    price = meta.get("regularMarketPrice")
                    prev_close = meta.get("chartPreviousClose")

                    if price is None or prev_close is None or prev_close == 0:
                        continue

                    change_percent = ((price - prev_close) / prev_close) * 100

                    closes = (
                        item["response"][0]
                        .get("indicators", {})
                        .get("quote", [{}])[0]
                        .get("close", [])
                    )
                    valid_closes = [c for c in closes if c is not None]
                    sparkline = valid_closes[-10:] if len(valid_closes) > 0 else []

                    parsed_results.append(
                        {
                            "ticker": symbol,
                            "price": price,
                            "change_percent": change_percent,
                            "sparkline": sparkline,
                        }
                    )
                    if change_percent > 0:
                        up_count += 1
                    elif change_percent < 0:
                        down_count += 1
            except httpx.HTTPError as e:
                logger.error(f"Error fetching batch {symbols} from yfinance: {e}")
                continue

    if not parsed_results:
        return None

    parsed_results.sort(key=lambda x: x["change_percent"], reverse=True)

    highs = parsed_results[:5]
    lows = parsed_results[-5:]
    lows.sort(key=lambda x: x["change_percent"])  # Sort lows ascending (worst first)

    return HighlightsData(
        timestamp=datetime.now(timezone.utc),
        highs_json=json.dumps(highs),
        lows_json=json.dumps(lows),
        fonte=mt5.fonte_efetiva("yfinance"),
        up_count=up_count,
        down_count=down_count,
        total_count=len(parsed_results),
    )


def collect_and_save() -> bool:
    logger.info("Starting highlights collection...")
    data = None
    if mt5.configurado():
        # MetaTrader 5 é a fonte preferencial; sem ele, segue a ordem antiga.
        with mt5.exclusivo():
            data = fetch_yfinance()
    if not data:
        logger.info("Falling back highlights to yfinance...")
        data = fetch_yfinance()

    if data:
        save_highlights_data(data)
        logger.info("Saved highlights data.")
        return True
    else:
        logger.error("Failed to collect highlights data from all sources.")
        return False


if __name__ == "__main__":
    success = collect_and_save()
    if not success:
        sys.exit(1)
