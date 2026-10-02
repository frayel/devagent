import json
import logging
import os
import sys
from datetime import datetime, timezone

import httpx

from app.database import FatorMolaData, save_fator_mola_data
from app.collectors.utils import fetch_with_retry
from app.collectors.highlights import TICKERS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch_yfinance() -> FatorMolaData | None:
    parsed_results = []

    # Batching tickers in groups of 15 to respect URL length and API limits
    batch_size = 15
    batches = [TICKERS[i : i + batch_size] for i in range(0, len(TICKERS), batch_size)]

    with httpx.Client(timeout=10.0) as client:
        for batch in batches:
            symbols = ",".join([f"{t}.SA" for t in batch])
            url = f"https://query1.finance.yahoo.com/v7/finance/spark?symbols={symbols}&range=1d&interval=1d"
            try:
                response = fetch_with_retry(url, client=client)
                data = response.json()

                for item in data.get("spark", {}).get("result", []):
                    if not item.get("response"):
                        continue

                    symbol = item.get("symbol", "").replace(".SA", "")
                    meta = item["response"][0].get("meta", {})
                    price = meta.get("regularMarketPrice")
                    low = meta.get("regularMarketDayLow")

                    if price is None or low is None or low == 0:
                        continue

                    if price <= low:
                        continue # Não recuperou ou recuperou menos que 0, não exibe

                    mola_percent = ((price - low) / low) * 100

                    # Se recuperou > 0, adiciona
                    if mola_percent > 0:
                        parsed_results.append(
                            {
                                "ticker": symbol,
                                "price": price,
                                "low": low,
                                "mola_percent": mola_percent,
                            }
                        )
            except httpx.HTTPError as e:
                logger.error(f"Error fetching batch {symbols} from yfinance: {e}")
                continue

    if not parsed_results:
        # Quando collectors funcionam mas os dados estão vazios, devem retornar array/objeto vazios (Fator Mola Data nula mas instanciada)
        return FatorMolaData(
            timestamp=datetime.now(timezone.utc),
            top3_json="[]",
            fonte="yfinance"
        )

    parsed_results.sort(key=lambda x: x["mola_percent"], reverse=True)

    top3 = parsed_results[:3]

    return FatorMolaData(
        timestamp=datetime.now(timezone.utc),
        top3_json=json.dumps(top3),
        fonte="yfinance"
    )

def fetch_brapi() -> FatorMolaData | None:
    BRAPI_TOKEN = os.environ.get("BRAPI_TOKEN")
    if not BRAPI_TOKEN:
        logger.warning("BRAPI_TOKEN not set, skipping brapi.dev for fator mola")
        return None

    tickers_str = ",".join(TICKERS)
    url = f"https://brapi.dev/api/quote/{tickers_str}?token={BRAPI_TOKEN}&fundamental=false"

    try:
        response = fetch_with_retry(url, timeout=15.0)
        data = response.json()

        if "results" not in data or not data["results"]:
            logger.error("Invalid response from brapi for fator mola")
            return None

        parsed_results = []
        for result in data["results"]:
            price = result.get("regularMarketPrice")
            low = result.get("regularMarketDayLow")

            if price is None or low is None or low == 0:
                continue

            if price <= low:
                continue

            mola_percent = ((price - low) / low) * 100

            if mola_percent > 0:
                parsed_results.append(
                    {
                        "ticker": result.get("symbol", ""),
                        "price": price,
                        "low": low,
                        "mola_percent": mola_percent,
                    }
                )

        if not parsed_results:
            return FatorMolaData(
                timestamp=datetime.now(timezone.utc),
                top3_json="[]",
                fonte="brapi"
            )

        parsed_results.sort(key=lambda x: x["mola_percent"], reverse=True)

        top3 = parsed_results[:3]

        return FatorMolaData(
            timestamp=datetime.now(timezone.utc),
            top3_json=json.dumps(top3),
            fonte="brapi"
        )
    except httpx.HTTPError as e:
        logger.error(f"Error fetching fator mola from brapi: {e}")
        return None

def collect_and_save() -> bool:
    logger.info("Starting fator mola collection...")
    # Prefer yfinance as fallback usually works well, let's just use yfinance as primary, brapi secondary
    data = fetch_yfinance()
    if not data:
        logger.info("Falling back fator mola to brapi...")
        data = fetch_brapi()

    if data:
        save_fator_mola_data(data)
        logger.info("Saved fator mola data.")
        return True
    else:
        logger.error("Failed to collect fator mola data from all sources.")
        return False

if __name__ == "__main__":
    success = collect_and_save()
    if not success:
        sys.exit(1)
