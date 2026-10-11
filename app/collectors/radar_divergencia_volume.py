import json
import logging
from datetime import datetime, timezone

import httpx

from app.database import RadarDivergenciaVolumeData, save_radar_divergencia_volume_data
from app.collectors import mt5
from app.collectors.utils import fetch_with_retry
from app.collectors.highlights import TICKERS

logger = logging.getLogger(__name__)


def fetch_yfinance() -> RadarDivergenciaVolumeData | None:
    parsed_results = []
    successful_fetches = 0

    with httpx.Client(timeout=10.0) as client:
        for ticker in TICKERS:
            symbol = f"{ticker}.SA"
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=5d&interval=1d"
            try:
                response = fetch_with_retry(url, client=client)
                data = response.json()

                result = data.get("chart", {}).get("result")
                if not result:
                    continue

                quote = result[0].get("indicators", {}).get("quote", [{}])[0]
                closes = quote.get("close", [])
                volumes = quote.get("volume", [])

                valid = [
                    (c, v)
                    for c, v in zip(closes, volumes)
                    if c is not None and v is not None
                ]

                if len(valid) < 5:
                    continue

                successful_fetches += 1

                first_close = valid[0][0]
                last_close = valid[-1][0]

                # Check for positive return over the 5 days
                if last_close <= first_close:
                    continue

                # Check for volume divergence (average of last 2 days < average of first 3 days)
                first_3_vol_avg = sum([v for _, v in valid[:3]]) / 3
                last_2_vol_avg = sum([v for _, v in valid[3:]]) / 2

                if first_3_vol_avg == 0:
                    continue

                if (
                    last_2_vol_avg < first_3_vol_avg * 0.8
                ):  # 20% drop at least to be significant
                    vol_var = (
                        (last_2_vol_avg - first_3_vol_avg) / first_3_vol_avg
                    ) * 100
                    price_var = ((last_close - first_close) / first_close) * 100

                    parsed_results.append(
                        {
                            "ticker": ticker,
                            "alta_acumulada": round(price_var, 2),
                            "var_volume": round(vol_var, 2),
                        }
                    )

            except Exception as e:
                logger.error(f"Error fetching {symbol} from yfinance: {e}")
                continue

    if successful_fetches == 0:
        return None

    # Sort by the most significant volume drop
    parsed_results.sort(key=lambda x: x["var_volume"])
    top_alerts = parsed_results[:3]

    return RadarDivergenciaVolumeData(
        timestamp=datetime.now(timezone.utc),
        alertas_json=json.dumps(top_alerts),
        fonte=mt5.fonte_efetiva("yfinance"),
    )


def collect_and_save() -> bool:
    logger.info("Starting radar_divergencia_volume collection...")
    data = fetch_yfinance()

    if data:
        save_radar_divergencia_volume_data(data)
        logger.info("Saved radar_divergencia_volume data.")
        return True
    else:
        logger.info("No radar_divergencia_volume data found or failed to collect.")
        return False
