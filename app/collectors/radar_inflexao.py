import json
import logging
from datetime import datetime, timezone
import httpx

from app.database import get_connection
from app.collectors.highlights import TICKERS
from app.collectors.utils import fetch_with_retry
from app.collectors import mt5

logger = logging.getLogger(__name__)


def collect_and_save() -> bool:
    parsed_results = []
    successful_fetches = 0
    batch_size = 15
    batches = [TICKERS[i : i + batch_size] for i in range(0, len(TICKERS), batch_size)]

    with httpx.Client(timeout=10.0) as client:
        for batch in batches:
            symbols = ",".join([f"{t}.SA" for t in batch])
            url = f"https://query1.finance.yahoo.com/v7/finance/spark?symbols={symbols}&range=1mo&interval=1d"
            try:
                response = fetch_with_retry(url, client=client)
                data = response.json()
                for item in data.get("spark", {}).get("result", []):
                    if not item.get("response"):
                        continue
                    symbol = item.get("symbol", "").replace(".SA", "")
                    try:
                        closes = item["response"][0]["indicators"]["quote"][0]["close"]
                    except (KeyError, IndexError):
                        continue

                    valid_closes = [v for v in closes if v is not None]

                    if len(valid_closes) < 16:
                        continue

                    d_0 = valid_closes[-1]
                    d_1 = valid_closes[-2]
                    d_15 = valid_closes[-16]

                    if not d_0 or not d_1 or not d_15 or d_1 == 0 or d_15 == 0:
                        continue

                    retorno_acumulado = ((d_1 - d_15) / d_15) * 100
                    variacao_hoje = ((d_0 - d_1) / d_1) * 100

                    if retorno_acumulado < -5 and variacao_hoje > 2:
                        parsed_results.append(
                            {
                                "ticker": symbol,
                                "variacao_hoje": round(variacao_hoje, 2),
                                "retorno_acumulado": round(retorno_acumulado, 2),
                            }
                        )
                successful_fetches += 1
            except Exception as e:
                logger.error(f"Error fetching batch {symbols} from yfinance: {e}")
                continue

    if successful_fetches == 0:
        return False

    parsed_results.sort(key=lambda x: x["retorno_acumulado"])
    top_5 = parsed_results[:5]

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS radar_inflexao_cache (
            timestamp TEXT PRIMARY KEY,
            alertas_json TEXT NOT NULL,
            fonte TEXT NOT NULL
        )
    """)
    cursor.execute(
        """
        INSERT INTO radar_inflexao_cache (timestamp, alertas_json, fonte)
        VALUES (?, ?, ?)
    """,
        (
            datetime.now(timezone.utc).isoformat(),
            json.dumps(top_5),
            mt5.fonte_efetiva("yfinance"),
        ),
    )
    conn.commit()
    conn.close()

    return True
