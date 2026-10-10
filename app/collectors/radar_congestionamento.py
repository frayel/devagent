import logging
import statistics

import httpx

from app.database import save_radar_congestionamento_data
from app.collectors.utils import fetch_with_retry
from app.collectors.highlights import TICKERS
from app.services.sparkline import build_sparkline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def collect_and_save() -> bool:
    fetch_yfinance()
    return True


def fetch_yfinance() -> None:
    batch_size = 15
    batches = [TICKERS[i : i + batch_size] for i in range(0, len(TICKERS), batch_size)]

    results = []

    with httpx.Client(timeout=10.0) as client:
        for batch in batches:
            symbols = ",".join([f"{t}.SA" for t in batch])
            url = f"https://query1.finance.yahoo.com/v7/finance/spark?symbols={symbols}&range=1mo&interval=1d"
            try:
                response = fetch_with_retry(url, client=client)
                data = response.json()

                if "spark" not in data or "result" not in data["spark"]:
                    continue

                for item in data["spark"]["result"]:
                    if not item or "response" not in item or not item["response"]:
                        continue

                    resp = item["response"][0]
                    if "indicators" not in resp or "quote" not in resp["indicators"]:
                        continue

                    symbol_sa = item.get("symbol", "")
                    ticker = symbol_sa.replace(".SA", "")

                    closes = resp["indicators"]["quote"][0].get("close", [])
                    valid_closes = [c for c in closes if c is not None]

                    if len(valid_closes) < 20:
                        continue

                    last_20_closes = valid_closes[-20:]

                    mean = statistics.mean(last_20_closes)
                    if mean == 0:
                        continue

                    stdev = statistics.stdev(last_20_closes)
                    bandwidth = stdev / mean

                    results.append(
                        {
                            "ticker": ticker,
                            "bandwidth": bandwidth,
                            "closes": last_20_closes,
                        }
                    )
            except Exception as e:
                logger.error(
                    f"Erro em fetch_yfinance no radar_congestionamento para o lote {batch}: {e}"
                )

    if not results:
        return

    results.sort(key=lambda x: x["bandwidth"])
    top_5 = results[:5]

    alertas = []
    for item in top_5:
        sparkline = build_sparkline(item["closes"])
        alertas.append(
            {
                "ticker": item["ticker"],
                "bandwidth": item["bandwidth"],
                "sparkline_path": sparkline["pontos"] if sparkline else "",
            }
        )

    save_radar_congestionamento_data(alertas, fonte="yfinance")
