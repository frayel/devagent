import json
import logging
import os
import sys
from datetime import datetime, timezone

import httpx

from app.database import HighlightsData, save_highlights_data

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
    "ELET3",
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
    "CPLE6",
    "UGPA3",
    "ENEV3",
    "TIMS3",
    "TOTS3",
    "EGIE3",
    "HAPV3",
]


def fetch_brapi() -> HighlightsData | None:
    BRAPI_TOKEN = os.environ.get("BRAPI_TOKEN")
    if not BRAPI_TOKEN:
        logger.warning("BRAPI_TOKEN not set, skipping brapi.dev for highlights")
        return None

    tickers_str = ",".join(TICKERS)
    url = f"https://brapi.dev/api/quote/{tickers_str}?token={BRAPI_TOKEN}&fundamental=false"

    try:
        response = httpx.get(url, timeout=15.0)
        response.raise_for_status()
        data = response.json()

        if "results" not in data or not data["results"]:
            logger.error("Invalid response from brapi for highlights")
            return None

        parsed_results = []
        for result in data["results"]:
            price = result.get("regularMarketPrice")
            prev_close = result.get("regularMarketPreviousClose")

            if price is None or prev_close is None or prev_close == 0:
                continue

            change_percent = ((price - prev_close) / prev_close) * 100

            parsed_results.append(
                {
                    "ticker": result.get("symbol", ""),
                    "price": price,
                    "change_percent": change_percent,
                }
            )

        if not parsed_results:
            return None

        # Sort by change percent
        parsed_results.sort(key=lambda x: x["change_percent"], reverse=True)

        highs = parsed_results[:5]
        lows = parsed_results[-5:]
        lows.sort(
            key=lambda x: x["change_percent"]
        )  # Sort lows ascending (worst first)

        return HighlightsData(
            timestamp=datetime.now(timezone.utc),
            highs_json=json.dumps(highs),
            lows_json=json.dumps(lows),
        )
    except httpx.HTTPError as e:
        logger.error(f"Error fetching highlights from brapi: {e}")
        return None


def fetch_yfinance() -> HighlightsData | None:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) B3Dashboard/1.0"
    }

    parsed_results = []

    with httpx.Client(headers=headers, timeout=10.0) as client:
        for ticker in TICKERS:
            url = f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}.SA?range=1d&interval=1d"
            try:
                response = client.get(url)
                response.raise_for_status()
                data = response.json()

                if (
                    "chart" not in data
                    or "result" not in data["chart"]
                    or not data["chart"]["result"]
                ):
                    continue

                meta = data["chart"]["result"][0]["meta"]
                price = meta.get("regularMarketPrice")
                prev_close = meta.get("chartPreviousClose")

                if price is None or prev_close is None or prev_close == 0:
                    continue

                change_percent = ((price - prev_close) / prev_close) * 100

                parsed_results.append(
                    {"ticker": ticker, "price": price, "change_percent": change_percent}
                )
            except httpx.HTTPError as e:
                logger.error(f"Error fetching {ticker} from yfinance: {e}")
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
    )


def collect_and_save() -> bool:
    logger.info("Starting highlights collection...")
    data = fetch_brapi()
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
