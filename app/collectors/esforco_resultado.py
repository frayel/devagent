import json
import logging
from datetime import datetime, timezone

import httpx

from app.database import EsforcoResultadoData, save_esforco_resultado_data
from app.collectors import mt5
from app.collectors.utils import fetch_with_retry
from app.collectors.highlights import TICKERS

logger = logging.getLogger(__name__)


def fetch_yfinance() -> EsforcoResultadoData | None:
    parsed_results = []
    successful_fetches = 0

    with httpx.Client(timeout=10.0) as client:
        for ticker in TICKERS:
            symbol = f"{ticker}.SA"
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=1mo&interval=1d"
            try:
                response = fetch_with_retry(url, client=client)
                data = response.json()

                result = data.get("chart", {}).get("result")
                if not result:
                    continue

                quote = result[0].get("indicators", {}).get("quote", [{}])[0]
                opens = quote.get("open", [])
                closes = quote.get("close", [])
                volumes = quote.get("volume", [])

                valid = [
                    (o, c, v)
                    for o, c, v in zip(opens, closes, volumes)
                    if o is not None and c is not None and v is not None
                ]

                if len(valid) < 2:
                    continue

                successful_fetches += 1

                last_session = valid[-1]
                last_open = last_session[0]
                last_close = last_session[1]
                last_volume = last_session[2]

                previous_sessions = valid[:-1][-20:]
                if not previous_sessions:
                    continue

                previous_volumes = [s[2] for s in previous_sessions]
                avg_volume = sum(previous_volumes) / len(previous_volumes)

                if avg_volume == 0 or last_open == 0:
                    continue

                vol_ratio = last_volume / avg_volume
                price_amplitude = abs(last_close - last_open) / last_open

                if vol_ratio > 1.5 and price_amplitude <= 0.005:
                    parsed_results.append(
                        {
                            "ticker": ticker,
                            "vol_ratio": round(vol_ratio, 2),
                            "price_var": round(
                                ((last_close - last_open) / last_open) * 100, 2
                            ),
                        }
                    )

            except Exception as e:
                logger.error(f"Error fetching {symbol} from yfinance: {e}")
                continue

    if successful_fetches == 0:
        return None

    parsed_results.sort(key=lambda x: x["vol_ratio"], reverse=True)
    top_alerts = parsed_results[:3]

    return EsforcoResultadoData(
        timestamp=datetime.now(timezone.utc),
        alertas_json=json.dumps(top_alerts),
        fonte=mt5.fonte_efetiva("yfinance"),
    )


def collect_and_save() -> bool:
    logger.info("Starting esforco_resultado collection...")
    data = fetch_yfinance()

    if data:
        save_esforco_resultado_data(data)
        logger.info("Saved esforco_resultado data.")
        return True
    else:
        logger.info("No esforco_resultado data found or failed to collect.")
        return False
