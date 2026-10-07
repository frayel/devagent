import json
import logging
from datetime import datetime, timezone

import httpx

from app.database import ForcaRelativaData, save_forca_relativa_data
from app.collectors import mt5
from app.collectors.utils import fetch_with_retry
from app.collectors.highlights import TICKERS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fetch_yfinance() -> ForcaRelativaData | None:
    # We need 30 trading days. 2 months is safe.
    range_str = "2mo"

    # We query ^BVSP separately because we want to make sure we have it
    ibov_url = f"https://query2.finance.yahoo.com/v8/finance/chart/^BVSP?range={range_str}&interval=1d"
    try:
        response = fetch_with_retry(ibov_url, timeout=10.0)
        ibov_data = response.json()
        result = ibov_data["chart"]["result"][0]
        closes = result["indicators"]["quote"][0]["close"]
        valid_closes = [c for c in closes if c is not None]
        if len(valid_closes) < 30:
            logger.warning("Not enough ^BVSP history for forca_relativa")
            return None

        ibov_history = valid_closes[-30:]
        ibov_return = (ibov_history[-1] / ibov_history[0]) - 1
    except Exception as e:
        logger.error(f"Error fetching ^BVSP for forca_relativa: {e}")
        return None

    batch_size = 15
    batches = [TICKERS[i : i + batch_size] for i in range(0, len(TICKERS), batch_size)]

    returns = []

    with httpx.Client(timeout=10.0) as client:
        for batch in batches:
            symbols = ",".join([f"{t}.SA" for t in batch])
            url = f"https://query1.finance.yahoo.com/v7/finance/spark?symbols={symbols}&range={range_str}&interval=1d"
            try:
                response = fetch_with_retry(url, client=client)
                data = response.json()

                for item in data.get("spark", {}).get("result", []):
                    if not item.get("response"):
                        continue

                    symbol = item.get("symbol", "").replace(".SA", "")
                    close_prices = (
                        item["response"][0]
                        .get("indicators", {})
                        .get("quote", [{}])[0]
                        .get("close", [])
                    )
                    valid_closes = [c for c in close_prices if c is not None]

                    if len(valid_closes) >= 30:
                        stock_history = valid_closes[-30:]
                        stock_return = (stock_history[-1] / stock_history[0]) - 1
                        forca_relativa = stock_return - ibov_return
                        returns.append(
                            {
                                "ticker": symbol,
                                "forca_relativa": forca_relativa,
                                "rentabilidade_acao": stock_return,
                                "rentabilidade_ibov": ibov_return,
                                "sparkline": valid_closes[-10:],
                            }
                        )

            except httpx.HTTPError as e:
                logger.error(f"Error fetching batch {symbols} for forca_relativa: {e}")

    if not returns:
        logger.warning("No valid returns for forca_relativa")
        return None

    maior = max(returns, key=lambda x: x["forca_relativa"])
    menor = min(returns, key=lambda x: x["forca_relativa"])

    maior_json = json.dumps(maior)
    menor_json = json.dumps(menor)

    return ForcaRelativaData(
        timestamp=datetime.now(timezone.utc),
        maior_json=maior_json,
        menor_json=menor_json,
        fonte=mt5.fonte_efetiva("yfinance"),
    )


def collect_and_save() -> bool:
    logger.info("Starting forca_relativa collection...")
    data = fetch_yfinance()
    if data:
        save_forca_relativa_data(data)
        logger.info("Saved forca_relativa data.")
        return True

    logger.error("Failed to collect forca_relativa data.")
    return False
