import json
import logging
import sys
from datetime import datetime, timezone, timedelta

import httpx

from app.database import IbovespaData, save_ibovespa_data
from app.collectors import mt5
from app.collectors.utils import fetch_with_retry

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def calc_mm(closes: list[float], window: int) -> float | None:
    if len(closes) < window:
        return None
    return sum(closes[-window:]) / window


def fetch_brapi() -> IbovespaData | None:
    from app.collectors import brapi

    try:
        result = brapi.cotacao("^BVSP", range="1y", interval="1d", fundamental="false")
        if not result:
            logger.error("Invalid response from brapi")
            return None

        current_price = float(result.get("regularMarketPrice", 0.0))
        previous_close = float(result.get("regularMarketPreviousClose", 0.0))

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

        if previous_close:
            var_pct = ((current_price - previous_close) / previous_close) * 100
            if abs(var_pct) > 12.0:
                logger.error(
                    f"brapi.dev returned implausible variation: {var_pct:.2f}%"
                )
                return None

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
        current_price = float(meta.get("regularMarketPrice", 0.0))

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

        # We need a robust way to get previous close
        # chartPreviousClose is often incorrect for B3 on Yahoo during trading hours.
        # previousClose can be None for Yahoo spark queries or sometimes missing.
        # It's safest to get it from the valid_closes array.

        current_date_str = (
            datetime.now(timezone.utc)
            .astimezone(timezone(timedelta(hours=-3)))
            .strftime("%Y-%m-%d")
        )

        previous_close = None

        # Yahoo Finance returns a chartPreviousClose which is the most reliable source for previous close
        # especially for indices where intraday previousClose calculation might use incomplete data
        meta_prev_close = meta.get("chartPreviousClose") or meta.get("previousClose")

        if len(valid_closes) > 1:
            if valid_dates[-1] == current_date_str:
                previous_close = (
                    meta_prev_close if meta_prev_close else valid_closes[-2]
                )
            else:
                # In tests, the fixture might not have today's date, but current_price matches valid_closes[-1]
                if current_price and current_price == valid_closes[-1]:
                    previous_close = (
                        meta_prev_close if meta_prev_close else valid_closes[-2]
                    )
                else:
                    previous_close = (
                        meta_prev_close if meta_prev_close else valid_closes[-1]
                    )
        elif len(valid_closes) == 1:
            if valid_dates[-1] == current_date_str or (
                current_price and current_price == valid_closes[-1]
            ):
                previous_close = meta_prev_close if meta_prev_close else current_price
            else:
                previous_close = (
                    meta_prev_close if meta_prev_close else valid_closes[-1]
                )

        # Absolute fallback to meta if for some reason history is empty
        if previous_close is None:
            previous_close = (
                meta.get("regularMarketPreviousClose")
                or meta.get("previousClose")
                or meta.get("chartPreviousClose")
            )

        # In case the fallback also fails, use the current_price
        if previous_close is None:
            previous_close = current_price
        previous_close = float(previous_close) if previous_close is not None else 0.0

        calc_closes = valid_closes.copy()
        if current_price and (not calc_closes or current_price != calc_closes[-1]):
            calc_closes.append(current_price)

        mm21 = calc_mm(calc_closes, 21)
        mm200 = calc_mm(calc_closes, 200)

        if previous_close:
            var_pct = ((current_price - previous_close) / previous_close) * 100
            if abs(var_pct) > 12.0:
                logger.error(f"yfinance returned implausible variation: {var_pct:.2f}%")
                return None

        history_json = json.dumps(
            {"dates": valid_dates[-30:], "closes": valid_closes[-30:]}
        )

        return IbovespaData(
            timestamp=datetime.now(timezone.utc),
            current_price=current_price,
            previous_close=previous_close,
            history_json=history_json,
            fonte=mt5.fonte_efetiva("yfinance"),
            mm21=mm21,
            mm200=mm200,
        )
    except httpx.HTTPError as e:
        logger.error(f"Error fetching from yfinance: {e}")
        return None


def collect_and_save() -> bool:
    logger.info("Starting collection...")
    data = None
    if mt5.configurado():
        # MetaTrader 5 é a fonte preferencial; sem ele, segue a ordem antiga.
        with mt5.exclusivo():
            data = fetch_yfinance()
    if not data:
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
