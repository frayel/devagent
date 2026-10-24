import json
import logging
import sys
from datetime import datetime, timezone

import httpx

from app.collectors import mt5
from app.collectors.highlights import TICKERS
from app.collectors.utils import fetch_historico_diario_yfinance_spark
from app.database import ExaustaoAltaData, save_exaustao_alta_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fetch_yfinance() -> ExaustaoAltaData | None:
    parsed_results = []
    successful_fetches = 0

    with httpx.Client(timeout=10.0) as client:
        try:
            results = fetch_historico_diario_yfinance_spark(TICKERS, "1d", "1d", client)
            for item in results:
                if not item.get("response"):
                    continue
                symbol = item.get("symbol", "").replace(".SA", "")
                try:
                    closes = item["response"][0]["indicators"]["quote"][0]["close"]
                    opens = item["response"][0]["indicators"]["quote"][0]["open"]
                    highs = item["response"][0]["indicators"]["quote"][0]["high"]
                except (KeyError, IndexError):
                    continue

                if not closes or not opens or not highs:
                    continue

                close = closes[-1]
                open_ = opens[-1]
                high = highs[-1]

                if close is None or open_ is None or high is None:
                    continue

                variacao = (close / open_) - 1
                if variacao < 0.02:
                    continue

                corpo = abs(close - open_)
                sombra_superior = high - max(open_, close)

                if sombra_superior >= 2 * corpo:
                    parsed_results.append(
                        {
                            "ticker": symbol,
                            "variacao": variacao * 100,
                        }
                    )
            successful_fetches += 1
        except httpx.HTTPError as e:
            logger.error(f"Error fetching from yfinance: {e}")

    if successful_fetches == 0:
        return None

    parsed_results.sort(key=lambda x: -x["variacao"])
    return ExaustaoAltaData(
        timestamp=datetime.now(timezone.utc),
        alertas_json=json.dumps(parsed_results),
        fonte=mt5.fonte_efetiva("yfinance"),
    )


def collect_and_save() -> bool:
    logger.info("Starting exaustao alta collection...")
    data = fetch_yfinance()
    if data:
        save_exaustao_alta_data(data)
        logger.info("Saved exaustao alta data.")
        return True
    logger.info("No exaustao alta data found or failed to collect.")
    return False


if __name__ == "__main__":
    if not collect_and_save():
        sys.exit(1)
