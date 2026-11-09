import json
import logging
from datetime import datetime, timezone

import httpx

from app.database import RadarAnomaliasSpreadData, save_radar_anomalias_spread_data
from app.collectors.utils import fetch_with_retry
from app.collectors.highlights import TICKERS

logger = logging.getLogger(__name__)

CESTA_LIQUIDEZ = TICKERS[:10]


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
    data = fetch_yfinance()

    if data:
        save_radar_anomalias_spread_data(data)
        logger.info("Saved anomalias spread data.")
        return True
    else:
        logger.error("Failed to collect anomalias spread data.")
        return False
