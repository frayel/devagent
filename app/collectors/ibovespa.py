import json
import logging
import os
import sys
from datetime import datetime, timezone

import httpx

from app.database import IbovespaData, save_ibovespa_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fetch_brapi() -> IbovespaData | None:
    BRAPI_TOKEN = os.environ.get("BRAPI_TOKEN")
    if not BRAPI_TOKEN:
        logger.warning("BRAPI_TOKEN not set, skipping brapi.dev")
        return None

    url = f"https://brapi.dev/api/quote/^BVSP?token={BRAPI_TOKEN}&range=1mo&interval=1d&fundamental=false"
    try:
        response = httpx.get(url, timeout=10.0)
        response.raise_for_status()
        data = response.json()

        if "results" not in data or not data["results"]:
            logger.error("Invalid response from brapi")
            return None

        result = data["results"][0]
        current_price = result.get("regularMarketPrice")
        previous_close = result.get("regularMarketPreviousClose")

        history = result.get("historicalDataPrice", [])
        if not history:
            logger.error("No historical data from brapi")
            return None

        # extract dates and closes
        dates = [
            datetime.fromtimestamp(h["date"], tz=timezone.utc).strftime("%Y-%m-%d")
            for h in history
            if "date" in h and "close" in h
        ]
        closes = [h["close"] for h in history if "date" in h and "close" in h]

        if not dates or not closes:
            return None

        history_json = json.dumps({"dates": dates[-30:], "closes": closes[-30:]})

        return IbovespaData(
            timestamp=datetime.now(timezone.utc),
            current_price=current_price,
            previous_close=previous_close,
            history_json=history_json,
            fonte="brapi",
        )
    except httpx.HTTPError as e:
        logger.error(f"Error fetching from brapi: {e}")
        return None


def fetch_yfinance() -> IbovespaData | None:
    url = (
        "https://query2.finance.yahoo.com/v8/finance/chart/^BVSP?range=1mo&interval=1d"
    )
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        response = httpx.get(url, headers=headers, timeout=10.0)
        response.raise_for_status()
        data = response.json()

        result = data["chart"]["result"][0]
        meta = result["meta"]
        current_price = meta.get("regularMarketPrice")
        previous_close = meta.get("chartPreviousClose")

        timestamps = result["timestamp"]
        closes = result["indicators"]["quote"][0]["close"]

        dates = [
            datetime.fromtimestamp(t, tz=timezone.utc).strftime("%Y-%m-%d")
            for t in timestamps
        ]

        # filter out None closes
        valid_history = [(d, c) for d, c in zip(dates, closes) if c is not None]
        valid_dates = [v[0] for v in valid_history]
        valid_closes = [v[1] for v in valid_history]

        history_json = json.dumps(
            {"dates": valid_dates[-30:], "closes": valid_closes[-30:]}
        )

        return IbovespaData(
            timestamp=datetime.now(timezone.utc),
            current_price=current_price,
            previous_close=previous_close,
            history_json=history_json,
            fonte="yfinance",
        )
    except httpx.HTTPError as e:
        logger.error(f"Error fetching from yfinance: {e}")
        return None


def collect_and_save() -> bool:
    logger.info("Starting collection...")
    data = fetch_brapi()
    if not data:
        logger.info("Falling back to yfinance...")
        data = fetch_yfinance()

    if data:
        save_ibovespa_data(data)
        logger.info(f"Saved Ibovespa data. Price: {data.current_price}")
        return True
    else:
        logger.error("Failed to collect data from all sources.")
        return False


if __name__ == "__main__":
    success = collect_and_save()
    if not success:
        sys.exit(1)
