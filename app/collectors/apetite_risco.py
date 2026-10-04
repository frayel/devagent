import logging
from datetime import datetime, timezone
import httpx
from app.database import ApetiteRiscoData, save_apetite_risco_data
from app.collectors.utils import fetch_with_retry

logger = logging.getLogger(__name__)


def fetch_yfinance() -> ApetiteRiscoData | None:
    url = "https://query1.finance.yahoo.com/v7/finance/spark?symbols=SMAL11.SA,%5EBVSP&range=1d&interval=1d"
    try:
        with httpx.Client(timeout=10.0) as client:
            response = fetch_with_retry(url, client=client)
            data = response.json()

            smal_var = None
            ibov_var = None

            for item in data.get("spark", {}).get("result", []):
                if not item.get("response"):
                    continue
                meta = item["response"][0].get("meta", {})
                prev_close = meta.get("chartPreviousClose")
                if prev_close is None:
                    continue
                closes = (
                    item["response"][0]
                    .get("indicators", {})
                    .get("quote", [{}])[0]
                    .get("close", [])
                )
                valid_closes = [c for c in closes if c is not None]
                if not valid_closes:
                    continue
                current_close = valid_closes[-1]
                var = (current_close - prev_close) / prev_close * 100

                if item["symbol"] == "SMAL11.SA":
                    smal_var = var
                elif item["symbol"] == "^BVSP":
                    ibov_var = var

            if smal_var is None or ibov_var is None:
                return None

            diferenca = smal_var - ibov_var
            if diferenca > 0:
                estado = "Tomando risco"
            else:
                estado = "Defensivo"

            return ApetiteRiscoData(
                timestamp=datetime.now(timezone.utc),
                estado=estado,
                diferenca=diferenca,
                fonte="yfinance",
            )
    except Exception as e:
        logger.error(f"Error fetching apetite risco: {e}")
        return None


def collect_and_save() -> bool:
    logger.info("Starting apetite risco collection...")
    data = fetch_yfinance()
    if data:
        save_apetite_risco_data(data)
        logger.info("Saved apetite risco data.")
        return True
    logger.error("Failed to collect apetite risco data.")
    return False


if __name__ == "__main__":
    collect_and_save()
