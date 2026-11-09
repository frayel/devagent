import json
import logging
import sys
from datetime import datetime, timezone

import httpx

from app.database import FatorMolaData, save_fator_mola_data
from app.collectors import mt5
from app.collectors.highlights import TICKERS
from app.collectors.utils import fetch_historico_diario_yfinance_spark

logger = logging.getLogger(__name__)


def fetch_yfinance() -> FatorMolaData | None:
    parsed_results = []

    with httpx.Client(timeout=10.0) as client:
        try:
            results = fetch_historico_diario_yfinance_spark(TICKERS, "1d", "1d", client)

            for item in results:
                if not item.get("response"):
                    continue

                symbol = item.get("symbol", "").replace(".SA", "")
                meta = item["response"][0].get("meta", {})
                price = meta.get("regularMarketPrice")
                low = meta.get("regularMarketDayLow")

                if price is None or low is None or low == 0:
                    continue

                if price <= low:
                    continue  # Não recuperou ou recuperou menos que 0, não exibe

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
        except Exception as e:
            logger.error(f"Error fetching from yfinance: {e}")

    if not parsed_results:
        # Quando collectors funcionam mas os dados estão vazios, devem retornar array/objeto vazios (Fator Mola Data nula mas instanciada)
        return FatorMolaData(
            timestamp=datetime.now(timezone.utc),
            top3_json="[]",
            fonte=mt5.fonte_efetiva("yfinance"),
        )

    parsed_results.sort(key=lambda x: x["mola_percent"], reverse=True)

    top3 = parsed_results[:3]

    return FatorMolaData(
        timestamp=datetime.now(timezone.utc),
        top3_json=json.dumps(top3),
        fonte=mt5.fonte_efetiva("yfinance"),
    )


def collect_and_save() -> bool:
    logger.info("Starting fator mola collection...")
    data = fetch_yfinance()

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
