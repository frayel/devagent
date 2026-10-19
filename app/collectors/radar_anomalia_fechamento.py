import json
import logging
import httpx

from app.database import save_radar_anomalia_fechamento_data
from app.collectors.highlights import TICKERS

logger = logging.getLogger(__name__)


def collect_and_save() -> bool:
    parsed_results = []

    with httpx.Client(timeout=10.0) as client:
        batch_size = 15
        batches = [
            TICKERS[i : i + batch_size] for i in range(0, len(TICKERS), batch_size)
        ]

        for batch in batches:
            symbols = ",".join([f"{t}.SA" for t in batch])
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbols}?range=2d&interval=5m"
            try:
                response = client.get(url)
                response.raise_for_status()
                data = response.json()
            except Exception as e:
                logger.error(
                    f"Erro ao buscar radar_anomalia_fechamento para query1: {e}"
                )
                url2 = f"https://query2.finance.yahoo.com/v8/finance/chart/{symbols}?range=2d&interval=5m"
                try:
                    response = client.get(url2)
                    response.raise_for_status()
                    data = response.json()
                except Exception as e2:
                    logger.error(
                        f"Erro ao buscar radar_anomalia_fechamento para query2: {e2}"
                    )
                    continue

            for item in data.get("chart", {}).get("result", []):
                symbol = item.get("meta", {}).get("symbol", "").replace(".SA", "")
                try:
                    closes = item["indicators"]["quote"][0]["close"]
                except KeyError:
                    continue

                valid_closes = [c for c in closes if c is not None]
                if len(valid_closes) >= 2:
                    preco_antes = valid_closes[-2]
                    fechamento = valid_closes[-1]
                    diff_pct = ((fechamento - preco_antes) / preco_antes) * 100
                    if abs(diff_pct) > 0.5:
                        parsed_results.append(
                            {
                                "ticker": symbol,
                                "diferenca_pct": diff_pct,
                                "preco_antes": preco_antes,
                                "fechamento": fechamento,
                            }
                        )

    parsed_results.sort(key=lambda x: abs(x["diferenca_pct"]), reverse=True)
    if parsed_results:
        save_radar_anomalia_fechamento_data(json.dumps(parsed_results[:5]), "yfinance")
    return True
