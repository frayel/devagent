import json
import logging
from datetime import datetime, timezone
import httpx

from app.database import (
    save_sobrevivencia_semanal_data,
    SobrevivenciaSemanalData,
)
from app.collectors.utils import fetch_with_retry
from app.collectors.highlights import TICKERS

logger = logging.getLogger(__name__)


def coletar() -> SobrevivenciaSemanalData | None:
    try:
        agora = datetime.now(timezone.utc)

        sobreviventes = []
        batch_size = 15
        batches = [
            TICKERS[i : i + batch_size] for i in range(0, len(TICKERS), batch_size)
        ]

        for batch in batches:
            tickers = ",".join(f"{t}.SA" for t in batch)
            url = f"https://query1.finance.yahoo.com/v7/finance/spark?symbols={tickers}&range=1mo&interval=1d"

            resp = fetch_with_retry(url)
            data = resp.json()

            if "spark" not in data or "result" not in data["spark"]:
                continue

            results = data["spark"]["result"]

            for result in results:
                symbol = result.get("symbol", "").replace(".SA", "")
                if not symbol:
                    continue

                resp_data = result.get("response", [{}])[0]
                if (
                    "indicators" not in resp_data
                    or "quote" not in resp_data["indicators"]
                ):
                    continue

                close_prices = resp_data["indicators"]["quote"][0].get("close", [])

                # Filter out None values
                valid_closes = [c for c in close_prices if c is not None]

                if len(valid_closes) < 6:
                    continue

                # Get the last 6 valid closes to have 5 daily returns
                last_6 = valid_closes[-6:]

                todas_altas = True
                for i in range(1, 6):
                    if last_6[i] <= last_6[i - 1]:
                        todas_altas = False
                        break

                if todas_altas:
                    sobreviventes.append({"ticker": symbol, "dias_consecutivos": 5})
        # Sort top 5 just in case, but spec asks for up to 5
        sobreviventes = sorted(sobreviventes, key=lambda x: x["ticker"])[:5]

        return SobrevivenciaSemanalData(
            timestamp=agora,
            alertas_json=json.dumps(sobreviventes),
            fonte="yfinance",
        )
    except httpx.HTTPError as e:
        logger.error(f"Erro HTTP na coleta de Sobrevivência Semanal via yfinance: {e}")
        return None
    except Exception as e:
        logger.error(
            f"Erro inesperado na coleta de Sobrevivência Semanal via yfinance: {e}"
        )
        return None


def collect_and_save() -> bool:
    data = coletar()
    if data is not None:
        save_sobrevivencia_semanal_data(data)
        return True
    return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    collect_and_save()
