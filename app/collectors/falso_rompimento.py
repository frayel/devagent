import json
import logging
from datetime import datetime, timezone

import httpx

from app.database import FalsoRompimentoData, save_falso_rompimento_data
from app.collectors import mt5
from app.collectors.utils import fetch_with_retry
from app.collectors.highlights import TICKERS

logger = logging.getLogger(__name__)


def fetch_yfinance() -> FalsoRompimentoData | None:
    parsed_results = []
    successful_fetches = 0

    with httpx.Client(timeout=10.0) as client:
        for i, ticker in enumerate(TICKERS):
            symbol = f"{ticker}.SA"
            subdomain = "query1" if i % 2 == 0 else "query2"
            url = f"https://{subdomain}.finance.yahoo.com/v8/finance/chart/{symbol}?range=2d&interval=1d"
            try:
                response = fetch_with_retry(url, client=client)
                data = response.json()

                result = data.get("chart", {}).get("result")
                if not result:
                    continue

                quote = result[0].get("indicators", {}).get("quote", [{}])[0]
                highs = quote.get("high", [])
                closes = quote.get("close", [])
                volumes = quote.get("volume", [])

                valid = [
                    (h, c, v)
                    for h, c, v in zip(highs, closes, volumes)
                    if h is not None and c is not None and v is not None
                ]

                if len(valid) < 2:
                    continue

                successful_fetches += 1

                # D-1 (yesterday)
                h_1, c_1, v_1 = valid[-2]

                # D-0 (today)
                h_0, c_0, v_0 = valid[-1]

                # Condição: Máxima D-0 > Máxima D-1 E Preço Atual D-0 < Preço Fechamento D-1 E Volume D-0 > Volume Médio D-1 (using Volume D-1)
                if h_0 > h_1 and c_0 < c_1 and v_0 > v_1:
                    price_var = ((c_0 - c_1) / c_1) * 100
                    vol_var = ((v_0 - v_1) / v_1) * 100

                    parsed_results.append(
                        {
                            "ticker": ticker,
                            "variacao": round(price_var, 2),
                            "var_volume": round(vol_var, 2),
                        }
                    )

            except Exception as e:
                logger.error(f"Error fetching {symbol} from yfinance: {e}")
                continue

    if successful_fetches == 0:
        return None

    # Sort by the most significant volume jump
    parsed_results.sort(key=lambda x: x["var_volume"], reverse=True)
    top_alerts = parsed_results[:3]

    return FalsoRompimentoData(
        timestamp=datetime.now(timezone.utc),
        alertas_json=json.dumps(top_alerts),
        fonte=mt5.fonte_efetiva("yfinance"),
    )


def collect_and_save() -> bool:
    logger.info("Starting falso_rompimento collection...")
    data = fetch_yfinance()

    if data:
        save_falso_rompimento_data(data)
        logger.info("Saved falso_rompimento data.")
        return True
    else:
        logger.info("No falso_rompimento data found or failed to collect.")
        return False
