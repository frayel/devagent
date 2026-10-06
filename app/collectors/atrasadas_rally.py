import json
import logging
import sys
from datetime import datetime, timezone
import httpx
from app.database import AtrasadasRallyData, save_atrasadas_rally_data
from app.collectors import mt5
from app.collectors.utils import fetch_with_retry
from app.collectors.highlights import TICKERS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fetch_yfinance() -> AtrasadasRallyData | None:
    # 5 pregões -> range=1mo garante que teremos histórico suficiente
    symbols = ",".join([f"{t}.SA" for t in TICKERS]) + ",^BVSP"
    url = f"https://query1.finance.yahoo.com/v7/finance/spark?symbols={symbols}&range=1mo&interval=1d"

    try:
        response = fetch_with_retry(url)
        data = response.json()

        results = data.get("spark", {}).get("result", [])
        if not results:
            return None

        history_map = {}
        for item in results:
            symbol = item.get("symbol", "").replace(".SA", "")
            resp = item.get("response", [])
            if not resp:
                continue

            try:
                closes = resp[0]["indicators"]["quote"][0]["close"]
                valid_closes = [c for c in closes if c is not None]
                if len(valid_closes) >= 5:
                    # Retorno percentual dos últimos 5 pregões
                    ret_5d = ((valid_closes[-1] / valid_closes[-5]) - 1) * 100
                    history_map[symbol] = ret_5d
            except (KeyError, IndexError):
                continue

        if "^BVSP" not in history_map:
            return None

        ibov_ret = history_map["^BVSP"]

        if ibov_ret <= 2.0:
            return AtrasadasRallyData(
                timestamp=datetime.now(timezone.utc),
                rally_valido=False,
                top3_json="[]",
                fonte=mt5.fonte_efetiva("yfinance"),
            )

        diffs = []
        for symbol, ret in history_map.items():
            if symbol == "^BVSP":
                continue
            diff = ibov_ret - ret
            if diff > 0:
                diffs.append({"ticker": symbol, "retorno": ret, "diferenca": diff})

        diffs.sort(key=lambda x: x["diferenca"], reverse=True)
        top3 = diffs[:3]

        return AtrasadasRallyData(
            timestamp=datetime.now(timezone.utc),
            rally_valido=True,
            top3_json=json.dumps(top3),
            fonte=mt5.fonte_efetiva("yfinance"),
        )

    except httpx.HTTPError as e:
        logger.error(f"Error fetching from yfinance: {e}")
        return None


def collect_and_save() -> bool:
    logger.info("Starting atrasadas rally collection...")
    data = fetch_yfinance()

    if data:
        save_atrasadas_rally_data(data)
        logger.info("Saved atrasadas rally data.")
        return True

    logger.error("Failed to collect atrasadas rally data.")
    return False


if __name__ == "__main__":
    success = collect_and_save()
    if not success:
        sys.exit(1)
