import json
import logging
import os
from datetime import datetime, timezone

import httpx

from app.database import RadarAnomaliasSpreadData, save_radar_anomalias_spread_data
from app.collectors.utils import fetch_with_retry
from app.collectors.highlights import TICKERS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CESTA_LIQUIDEZ = TICKERS[:10]


def fetch_brapi() -> RadarAnomaliasSpreadData | None:
    BRAPI_TOKEN = os.environ.get("BRAPI_TOKEN")
    if not BRAPI_TOKEN:
        logger.warning("BRAPI_TOKEN not set, skipping brapi.dev for anomalias spread")
        return None

    tickers_str = ",".join(CESTA_LIQUIDEZ)
    url = f"https://brapi.dev/api/quote/{tickers_str}?token={BRAPI_TOKEN}&fundamental=false"

    try:
        response = fetch_with_retry(url, timeout=15.0)
        data = response.json()

        if "results" not in data or not data["results"]:
            logger.error("Invalid response from brapi for anomalias spread")
            return None

        parsed_results = []
        for result in data["results"]:
            ask = result.get("regularMarketDayHigh")
            bid = result.get("regularMarketDayLow")

            ask = result.get("ask", ask)
            bid = result.get("bid", bid)

            if ask is None or bid is None or bid == 0:
                continue

            volume = result.get("regularMarketVolume", 0)
            if volume == 0:
                continue

            spread_percent = ((ask - bid) / bid) * 100

            if spread_percent > 0.5:
                parsed_results.append(
                    {
                        "ticker": result.get("symbol", ""),
                        "spread_percent": spread_percent,
                    }
                )

        parsed_results.sort(key=lambda x: x["spread_percent"], reverse=True)
        top5 = parsed_results[:5]

        return RadarAnomaliasSpreadData(
            timestamp=datetime.now(timezone.utc),
            alertas_json=json.dumps(top5),
            fonte="brapi",
        )
    except httpx.HTTPError as e:
        logger.error(f"Error fetching anomalias spread from brapi: {e}")
        return None


def fetch_yfinance() -> RadarAnomaliasSpreadData | None:
    parsed_results = []
    tickers_str = ",".join([f"{t}.SA" for t in CESTA_LIQUIDEZ])
    url = f"https://query1.finance.yahoo.com/v8/finance/spark?symbols={tickers_str}&range=1d&interval=1d"
    try:
        response = fetch_with_retry(url)
        data = response.json()
        for item in data.get("spark", {}).get("result", []):
            if not item.get("response"):
                continue
            meta = item["response"][0].get("meta", {})

            ask = meta.get("regularMarketDayHigh")
            bid = meta.get("regularMarketDayLow")

            if ask is None or bid is None or bid == 0:
                continue

            spread_percent = ((ask - bid) / bid) * 100

            if spread_percent > 0.5:
                parsed_results.append(
                    {
                        "ticker": item.get("symbol", "").replace(".SA", ""),
                        "spread_percent": spread_percent,
                    }
                )

        parsed_results.sort(key=lambda x: x["spread_percent"], reverse=True)
        top5 = parsed_results[:5]

        return RadarAnomaliasSpreadData(
            timestamp=datetime.now(timezone.utc),
            alertas_json=json.dumps(top5),
            fonte="yfinance",
        )
    except httpx.HTTPError as e:
        logger.error(f"Error fetching anomalias spread from yfinance: {e}")
        return None


def collect_and_save() -> bool:
    logger.info("Starting anomalias spread collection...")
    data = fetch_brapi()
    if not data:
        data = fetch_yfinance()

    if data:
        save_radar_anomalias_spread_data(data)
        logger.info("Saved anomalias spread data.")
        return True
    else:
        logger.error("Failed to collect anomalias spread data.")
        return False
