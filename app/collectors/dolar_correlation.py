import json
import logging
from datetime import datetime, timezone
import math

from app.database import DolarCorrelationData, save_dolar_correlation_data
from app.collectors.utils import fetch_with_retry
from app.collectors.highlights import TICKERS

logger = logging.getLogger(__name__)


def fetch_yfinance_history(tickers: list[str]) -> list[dict]:
    symbols = ",".join(tickers)
    url = f"https://query1.finance.yahoo.com/v7/finance/spark?symbols={symbols}&range=2mo&interval=1d"

    try:
        response = fetch_with_retry(url, timeout=15.0)
        data = response.json()
        return data.get("spark", {}).get("result", [])
    except Exception as e:
        logger.error(f"Error fetching spark data for dolar correlation: {e}")
        return []


def calculate_returns(closes: list[float]) -> list[float]:
    returns = []
    for i in range(1, len(closes)):
        if closes[i - 1] != 0:
            returns.append((closes[i] - closes[i - 1]) / closes[i - 1])
        else:
            returns.append(0.0)
    return returns


def calculate_pearson(x: list[float], y: list[float]) -> float:
    n = len(x)
    if n == 0 or n != len(y):
        return 0.0
    sum_x = sum(x)
    sum_y = sum(y)
    sum_xy = sum(i * j for i, j in zip(x, y))
    sum_x_sq = sum(i**2 for i in x)
    sum_y_sq = sum(i**2 for i in y)

    numerator = (n * sum_xy) - (sum_x * sum_y)
    denominator = math.sqrt(((n * sum_x_sq) - sum_x**2) * ((n * sum_y_sq) - sum_y**2))

    if denominator == 0:
        return 0.0
    return numerator / denominator


def collect_and_save() -> bool:
    logger.info("Starting dolar correlation collection...")

    # fetch dollar
    dollar_res = fetch_yfinance_history(["BRL=X"])
    if not dollar_res:
        save_dolar_correlation_data(
            DolarCorrelationData(
                timestamp=datetime.now(timezone.utc),
                positivas_json="[]",
                negativas_json="[]",
                fonte="yfinance",
            )
        )
        return False

    dollar_item = dollar_res[0]
    dollar_closes = (
        dollar_item.get("response", [{}])[0]
        .get("indicators", {})
        .get("quote", [{}])[0]
        .get("close", [])
    )
    dollar_dates = dollar_item.get("response", [{}])[0].get("timestamp", [])

    # filter out Nones
    d_valid = [(d, c) for d, c in zip(dollar_dates, dollar_closes) if c is not None]
    if len(d_valid) < 30:
        save_dolar_correlation_data(
            DolarCorrelationData(
                timestamp=datetime.now(timezone.utc),
                positivas_json="[]",
                negativas_json="[]",
                fonte="yfinance",
            )
        )
        return False

    d_dates = [x[0] for x in d_valid][-30:]

    # fetch stocks
    # Batch size 15 for safety
    batch_size = 15
    batches = [
        [f"{t}.SA" for t in TICKERS[i : i + batch_size]]
        for i in range(0, len(TICKERS), batch_size)
    ]

    correlations = []

    for batch in batches:
        stocks_res = fetch_yfinance_history(batch)
        for item in stocks_res:
            symbol = item.get("symbol", "").replace(".SA", "")
            s_closes = (
                item.get("response", [{}])[0]
                .get("indicators", {})
                .get("quote", [{}])[0]
                .get("close", [])
            )
            s_dates = item.get("response", [{}])[0].get("timestamp", [])

            s_dict = {d: c for d, c in zip(s_dates, s_closes) if c is not None}

            # Intersection of dates
            common_dates = sorted(list(set(d_dates).intersection(set(s_dict.keys()))))

            if len(common_dates) >= 15:
                s_common = [s_dict[d] for d in common_dates]
                # for dollar we need to extract from the valid array
                # wait, dollar_returns is pre-calculated over d_valid.
                # If we recalculate returns on intersection, it's safer.
                d_dict = {x[0]: x[1] for x in d_valid}
                d_common = [d_dict[d] for d in common_dates]

                s_returns = calculate_returns(s_common)
                d_returns = calculate_returns(d_common)

                corr = calculate_pearson(s_returns, d_returns)
                correlations.append({"ticker": symbol, "correlation": corr})

    if not correlations:
        save_dolar_correlation_data(
            DolarCorrelationData(
                timestamp=datetime.now(timezone.utc),
                positivas_json="[]",
                negativas_json="[]",
                fonte="yfinance",
            )
        )
        return False

    correlations.sort(key=lambda x: x["correlation"], reverse=True)

    positivas = [c for c in correlations if c["correlation"] > 0][:3]
    negativas = [c for c in correlations if c["correlation"] < 0]
    negativas.sort(key=lambda x: x["correlation"])
    negativas = negativas[:3]

    data = DolarCorrelationData(
        timestamp=datetime.now(timezone.utc),
        positivas_json=json.dumps(positivas),
        negativas_json=json.dumps(negativas),
        fonte="yfinance",
    )
    save_dolar_correlation_data(data)
    logger.info("Saved dolar correlation data.")
    return True


if __name__ == "__main__":
    collect_and_save()
