import json
import logging
from datetime import datetime, timezone
import httpx

from app.database import RadarShortSqueezeData, save_radar_short_squeeze_data
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
                        volumes = item["response"][0]["indicators"]["quote"][0][
                            "volume"
                        ]
                    except (KeyError, IndexError):
                        continue

                    # zip and filter Nones
                    valid = [
                        (c, v)
                        for c, v in zip(closes, volumes)
                        if c is not None and v is not None
                    ]

                    if len(valid) < 11:
                        continue

                    c_0 = valid[-1][0]
                    v_0 = valid[-1][1]
                    c_1 = valid[-2][0]
                    c_10 = valid[-11][0]

                    if c_1 == 0 or c_10 == 0:
                        continue

                    variacao_10_dias = ((c_1 - c_10) / c_10) * 100
                    variacao_hoje = ((c_0 - c_1) / c_1) * 100

                    vol_10_dias = [v[1] for v in valid[-11:-1]]
                    avg_vol = sum(vol_10_dias) / len(vol_10_dias) if vol_10_dias else 0

                    if avg_vol == 0:
                        continue

                    mult_vol = v_0 / avg_vol

                    if variacao_10_dias <= -10 and variacao_hoje >= 4 and mult_vol >= 2:
                        parsed_results.append(
                            {
                                "ticker": symbol,
                                "alta_hoje": round(variacao_hoje, 2),
                                "mult_vol": round(mult_vol, 1),
                                "queda_10d": round(variacao_10_dias, 2),
                            }
                        )
                successful_fetches += 1
            except Exception as e:
                logger.error(f"Error fetching batch {symbols} from yfinance: {e}")
                continue

    if successful_fetches == 0:
        return False

    parsed_results.sort(key=lambda x: x["alta_hoje"], reverse=True)
    top = parsed_results[:5]

    save_radar_short_squeeze_data(
        RadarShortSqueezeData(
            timestamp=datetime.now(timezone.utc),
            alertas_json=json.dumps(top),
            fonte=mt5.fonte_efetiva("yfinance"),
        )
    )

    return True
