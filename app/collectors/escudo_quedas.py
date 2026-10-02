import json
import logging
from datetime import datetime, timezone
import httpx
from app.database import EscudoQuedasData, save_escudo_quedas_data
from app.collectors.utils import fetch_with_retry
from app.collectors.highlights import TICKERS

logger = logging.getLogger(__name__)


def fetch_yfinance() -> EscudoQuedasData | None:
    range_str = "2mo"
    ibov_url = f"https://query2.finance.yahoo.com/v8/finance/chart/^BVSP?range={range_str}&interval=1d"

    try:
        response = fetch_with_retry(ibov_url, timeout=10.0)
        ibov_data = response.json()
        result = ibov_data["chart"]["result"][0]
        closes = result["indicators"]["quote"][0]["close"]
        timestamps = result["timestamp"]

        valid_data = [(ts, c) for ts, c in zip(timestamps, closes) if c is not None]
        if len(valid_data) < 30:
            logger.warning("Not enough ^BVSP history for escudo_quedas")
            return None

        valid_data = valid_data[-30:]

        ibov_negative_dates = []
        for i in range(1, len(valid_data)):
            ret = (valid_data[i][1] / valid_data[i - 1][1]) - 1
            if ret < 0:
                ibov_negative_dates.append(valid_data[i][0])

        if not ibov_negative_dates:
            logger.warning("No negative days for ^BVSP in the period")
            return None

    except Exception as e:
        logger.error(f"Error fetching ^BVSP for escudo_quedas: {e}")
        return None

    batch_size = 15
    batches = [TICKERS[i : i + batch_size] for i in range(0, len(TICKERS), batch_size)]

    stock_stats = []

    with httpx.Client(timeout=10.0) as client:
        for batch in batches:
            symbols = ",".join([f"{t}.SA" for t in batch])
            url = f"https://query1.finance.yahoo.com/v7/finance/spark?symbols={symbols}&range={range_str}&interval=1d"
            try:
                response = fetch_with_retry(url, client=client)
                data = response.json()

                for item in data.get("spark", {}).get("result", []):
                    if not item.get("response"):
                        continue

                    symbol = item.get("symbol", "").replace(".SA", "")
                    resp_data = item["response"][0]

                    if "indicators" not in resp_data or "timestamp" not in resp_data:
                        continue

                    stock_closes = resp_data["indicators"]["quote"][0].get("close", [])
                    stock_timestamps = resp_data["timestamp"]

                    stock_valid_data = {
                        ts: c
                        for ts, c in zip(stock_timestamps, stock_closes)
                        if c is not None
                    }

                    positive_count = 0
                    returns_on_negative_days = []

                    for ts in ibov_negative_dates:
                        # Find the index of this timestamp in the stock's data
                        try:
                            idx = stock_timestamps.index(ts)
                            if idx > 0:
                                prev_ts = stock_timestamps[idx - 1]
                                curr_close = stock_valid_data.get(ts)
                                prev_close = stock_valid_data.get(prev_ts)

                                if (
                                    curr_close is not None
                                    and prev_close is not None
                                    and prev_close > 0
                                ):
                                    stock_ret = (curr_close / prev_close) - 1
                                    returns_on_negative_days.append(stock_ret)
                                    if stock_ret > 0:
                                        positive_count += 1
                        except ValueError:
                            pass

                    if returns_on_negative_days:
                        avg_ret = sum(returns_on_negative_days) / len(
                            returns_on_negative_days
                        )
                        stock_stats.append(
                            {
                                "ticker": symbol,
                                "dias_positivos": positive_count,
                                "retorno_medio": avg_ret,
                            }
                        )

            except Exception as e:
                logger.error(f"Error fetching batch {symbols} for escudo_quedas: {e}")

    if not stock_stats:
        logger.warning("No stock stats calculated for escudo_quedas")
        return None

    stock_stats.sort(
        key=lambda x: (x["dias_positivos"], x["retorno_medio"]), reverse=True
    )
    top3 = stock_stats[:3]

    final_data = {"qtd_quedas_ibov": len(ibov_negative_dates), "top3": top3}

    return EscudoQuedasData(
        timestamp=datetime.now(timezone.utc),
        top3_json=json.dumps(final_data),
        fonte="yfinance",
    )


def collect_and_save() -> bool:
    logger.info("Starting escudo_quedas collection...")
    data = fetch_yfinance()
    if data:
        save_escudo_quedas_data(data)
        logger.info("Saved escudo_quedas data.")
        return True
    logger.error("Failed to collect escudo_quedas data.")
    return False
