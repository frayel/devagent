import logging
from datetime import datetime, timezone
import httpx

from app.database import RotacaoCapitalData, save_rotacao_capital_data
from app.collectors import mt5
from app.collectors.utils import fetch_with_retry

logger = logging.getLogger(__name__)


def fetch_yfinance() -> RotacaoCapitalData | None:
    bancos = ["ITUB4.SA", "BBDC4.SA", "BBAS3.SA"]
    commodities = ["VALE3.SA", "PETR4.SA", "PRIO3.SA"]
    symbols = ",".join(bancos + commodities)

    url = f"https://query1.finance.yahoo.com/v7/finance/spark?symbols={symbols}&range=1d&interval=1d"

    try:
        with httpx.Client(timeout=10.0) as client:
            response = fetch_with_retry(url, client=client)
            data = response.json()

            bancos_vars = []
            commodities_vars = []

            for item in data.get("spark", {}).get("result", []):
                if not item.get("response"):
                    continue
                meta = item["response"][0].get("meta", {})
                prev_close = meta.get("chartPreviousClose")
                if prev_close is None or prev_close == 0:
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
                var = ((current_close - prev_close) / prev_close) * 100

                symbol = item["symbol"]
                if symbol in bancos:
                    bancos_vars.append(var)
                elif symbol in commodities:
                    commodities_vars.append(var)

            if not bancos_vars or not commodities_vars:
                return None

            avg_bancos = sum(bancos_vars) / len(bancos_vars)
            avg_commodities = sum(commodities_vars) / len(commodities_vars)

            estado = "Neutra"
            if avg_bancos > 0.5 and avg_commodities < -0.5:
                estado = "Para Bancos"
            elif avg_commodities > 0.5 and avg_bancos < -0.5:
                estado = "Para Commodities"

            return RotacaoCapitalData(
                timestamp=datetime.now(timezone.utc),
                estado=estado,
                var_bancos=avg_bancos,
                var_commodities=avg_commodities,
                fonte=mt5.fonte_efetiva("yfinance"),
            )
    except Exception as e:
        logger.error(f"Error fetching rotacao capital: {e}")
        return None


def collect_and_save() -> bool:
    logger.info("Starting rotacao capital collection...")
    data = fetch_yfinance()
    if data:
        save_rotacao_capital_data(data)
        logger.info("Saved rotacao capital data.")
        return True
    logger.error("Failed to collect rotacao capital data.")
    return False


if __name__ == "__main__":
    collect_and_save()
