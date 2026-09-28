import json
import logging
import os
import sys
from datetime import datetime, timezone

import httpx

from app.database import IbovespaData, save_ibovespa_data
from app.collectors.utils import fetch_with_retry

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def calc_mm(closes: list[float], window: int) -> float | None:
    if len(closes) < window:
        return None
    return sum(closes[-window:]) / window


def fetch_brapi() -> IbovespaData | None:
    BRAPI_TOKEN = os.environ.get("BRAPI_TOKEN")
    if not BRAPI_TOKEN:
        logger.warning("BRAPI_TOKEN not set, skipping brapi.dev")
        return None

    url = f"https://brapi.dev/api/quote/%5EBVSP?token={BRAPI_TOKEN}&range=1y&interval=1d&fundamental=false"
    try:
        response = fetch_with_retry(url, timeout=10.0)
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

        # Calculate moving averages
        # Append current price to closes if it's not already closed (current_price not exactly the last close)
        calc_closes = closes.copy()
        if current_price and (not calc_closes or current_price != calc_closes[-1]):
            calc_closes.append(current_price)

        mm21 = calc_mm(calc_closes, 21)
        mm200 = calc_mm(calc_closes, 200)

        history_json = json.dumps({"dates": dates[-30:], "closes": closes[-30:]})

        return IbovespaData(
            timestamp=datetime.now(timezone.utc),
            current_price=current_price,
            previous_close=previous_close,
            history_json=history_json,
            fonte="brapi",
            mm21=mm21,
            mm200=mm200,
        )
    except httpx.HTTPError as e:
        logger.error(f"Error fetching from brapi: {e}")
        return None


def fetch_yfinance() -> IbovespaData | None:
    url = "https://query2.finance.yahoo.com/v8/finance/chart/^BVSP?range=1y&interval=1d"
    try:
        response = fetch_with_retry(url, timeout=10.0)
        data = response.json()

        result = data["chart"]["result"][0]
        meta = result["meta"]
        current_price = meta.get("regularMarketPrice")

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

        if len(valid_closes) > 1:
            previous_close = valid_closes[-2]
        else:
            previous_close = meta.get("previousClose") or meta.get("chartPreviousClose")

        calc_closes = valid_closes.copy()
        if current_price and (not calc_closes or current_price != calc_closes[-1]):
            calc_closes.append(current_price)

        mm21 = calc_mm(calc_closes, 21)
        mm200 = calc_mm(calc_closes, 200)

        history_json = json.dumps(
            {"dates": valid_dates[-30:], "closes": valid_closes[-30:]}
        )

        return IbovespaData(
            timestamp=datetime.now(timezone.utc),
            current_price=current_price,
            previous_close=previous_close,
            history_json=history_json,
            fonte="yfinance",
            mm21=mm21,
            mm200=mm200,
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
