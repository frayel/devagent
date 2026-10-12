import json
import logging
import sys
from datetime import datetime, timezone

import httpx

from app.database import RadarAbsorcaoCruzadaData, save_radar_absorcao_cruzada_data
from app.collectors import mt5
from app.collectors.utils import fetch_with_retry
from app.collectors.highlights import TICKERS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fetch_yfinance() -> RadarAbsorcaoCruzadaData | None:
    parsed_results = []
    successful_fetches = 0

    with httpx.Client(timeout=10.0) as client:
        for i, symbol in enumerate(TICKERS):
            yf_symbol = f"{symbol}.SA"
            subdomain = "query1" if i % 2 == 0 else "query2"
            url = f"https://{subdomain}.finance.yahoo.com/v8/finance/chart/{yf_symbol}?range=5d&interval=15m"
            try:
                response = fetch_with_retry(url, client=client)
                data = response.json()
                successful_fetches += 1

                result_list = data.get("chart", {}).get("result", [])
                if not result_list:
                    continue

                for item in result_list:
                    try:
                        timestamp = item["timestamp"]
                        quote = item["indicators"]["quote"][0]
                        volumes = quote["volume"]
                        closes = quote["close"]
                        opens = quote["open"]
                        lows = quote["low"]
                        highs = quote["high"]
                    except KeyError:
                        continue

                    # Zip data together and skip nulls
                    valid_history = [
                        (t, o, h, lo, c, v)
                        for t, o, h, lo, c, v in zip(
                            timestamp, opens, highs, lows, closes, volumes
                        )
                        if v is not None
                        and c is not None
                        and o is not None
                        and lo is not None
                        and h is not None
                    ]

                    if len(valid_history) < 10:
                        continue

                    # Find data points belonging to the current day (assuming chronological order)
                    # We can use the date part of the timestamp
                    current_day_date = datetime.fromtimestamp(
                        valid_history[-1][0], tz=timezone.utc
                    ).date()

                    current_day_data = []
                    prev_days_data = []

                    for row in valid_history:
                        row_date = datetime.fromtimestamp(
                            row[0], tz=timezone.utc
                        ).date()
                        if row_date == current_day_date:
                            current_day_data.append(row)
                        else:
                            prev_days_data.append(row)

                    if not current_day_data or not prev_days_data:
                        continue

                    # Calculate drop from previous day's close
                    prev_close = prev_days_data[-1][4]
                    current_close = current_day_data[-1][4]

                    if prev_close == 0:
                        continue

                    drop_pct = ((current_close / prev_close) - 1) * 100
                    if drop_pct >= -1.5:
                        continue

                    # Find the candle with the minimum low of the current day
                    min_low_candle = min(current_day_data, key=lambda x: x[3])
                    min_low_volume = min_low_candle[5]

                    # Calculate average volume of down-candles in previous days
                    down_candles_prev_days = [
                        row for row in prev_days_data if row[4] < row[1]
                    ]  # close < open
                    if not down_candles_prev_days:
                        continue

                    avg_down_volume = sum(
                        row[5] for row in down_candles_prev_days
                    ) / len(down_candles_prev_days)

                    if avg_down_volume == 0:
                        continue

                    ratio = min_low_volume / avg_down_volume

                    if ratio > 2.0:
                        parsed_results.append(
                            {"ticker": symbol, "ratio": ratio, "drop_pct": drop_pct}
                        )

            except httpx.HTTPError as e:
                logger.error(f"Error fetching {yf_symbol} from yfinance: {e}")
                continue

    if successful_fetches == 0:
        return None

    parsed_results.sort(key=lambda x: x["ratio"], reverse=True)
    top_alerts = parsed_results[:3]

    return RadarAbsorcaoCruzadaData(
        timestamp=datetime.now(timezone.utc),
        alertas_json=json.dumps(top_alerts),
        fonte=mt5.fonte_efetiva("yfinance"),
    )


def collect_and_save() -> bool:
    logger.info("Starting Radar de Absorção Cruzada collection...")
    data = fetch_yfinance()

    if data:
        save_radar_absorcao_cruzada_data(data)
        logger.info("Saved radar_absorcao_cruzada data.")
        return True
    else:
        logger.info("No radar_absorcao_cruzada data found or failed to collect.")
        return False


if __name__ == "__main__":
    success = collect_and_save()
    if not success:
        sys.exit(1)
