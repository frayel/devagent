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
    range_str = "1mo"

    ibov_url = f"https://query2.finance.yahoo.com/v8/finance/chart/^BVSP?range={range_str}&interval=1d"
    try:
        response = fetch_with_retry(ibov_url, timeout=10.0)
        ibov_data = response.json()
        result = ibov_data["chart"]["result"][0]
        closes = result["indicators"]["quote"][0]["close"]
        valid_closes = [c for c in closes if c is not None]
        if len(valid_closes) < 5:
            logger.warning("Not enough ^BVSP history for atrasadas_rally")
            return None

        ibov_history = valid_closes[-5:]
        ibov_ret = ((ibov_history[-1] / ibov_history[0]) - 1) * 100
    except Exception as e:
        logger.error(f"Error fetching ^BVSP for atrasadas_rally: {e}")
        return None

    if ibov_ret <= 2.0:
        return AtrasadasRallyData(
            timestamp=datetime.now(timezone.utc),
            rally_valido=False,
            top3_json="[]",
            fonte=mt5.fonte_efetiva("yfinance"),
        )

    batch_size = 15
    batches = [TICKERS[i : i + batch_size] for i in range(0, len(TICKERS), batch_size)]

    history_map = {}

    with httpx.Client(timeout=10.0) as client:
        for batch in batches:
            symbols = ",".join([f"{t}.SA" for t in batch])
            url = f"https://query1.finance.yahoo.com/v8/finance/spark?symbols={symbols}&range={range_str}&interval=1d"
            try:
                response = fetch_with_retry(url, client=client)
                data = response.json()

                for item in data.get("spark", {}).get("result", []):
                    if not item.get("response"):
                        continue

                    symbol = item.get("symbol", "").replace(".SA", "")
                    try:
                        close_prices = (
                            item["response"][0]
                            .get("indicators", {})
                            .get("quote", [{}])[0]
                            .get("close", [])
                        )
                        valid_closes = [c for c in close_prices if c is not None]

                        if len(valid_closes) >= 5:
                            ret_5d = ((valid_closes[-1] / valid_closes[-5]) - 1) * 100
                            history_map[symbol] = ret_5d
                    except (KeyError, IndexError):
                        continue
            except httpx.HTTPError as e:
                logger.error(f"Error fetching batch {symbols} for atrasadas_rally: {e}")

    diffs = []
    for symbol, ret in history_map.items():
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
