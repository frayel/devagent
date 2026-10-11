import json
import logging
import math
from datetime import datetime, timezone

from app.database import SensibilidadeJurosData, save_sensibilidade_juros_data
from app.collectors import mt5
from app.collectors.utils import fetch_with_retry

logger = logging.getLogger(__name__)

TICKERS_SENSIVEIS = [
    "LREN3",
    "MGLU3",
    "PETZ3",
    "BHIA3",
    "EZTC3",
    "CYRE3",
    "MRVE3",
    "TEND3",
    "DIRR3",
    "CVCB3",
    "RENT3",
    "NTCO3",
    "ALOS3",
    "SOMA3",
    "ARZZ3",
    "SMFT3",
    "LWSA3",
    "CASH3",
    "BMOB3",
    "TOTS3",
]


def fetch_yfinance_history(tickers: list[str]) -> list[dict]:
    symbols = ",".join(tickers)
    url = f"https://query1.finance.yahoo.com/v7/finance/spark?symbols={symbols}&range=2mo&interval=1d"
    try:
        response = fetch_with_retry(url, timeout=15.0)
        data = response.json()
        return data.get("spark", {}).get("result", [])
    except Exception as e:
        logger.error(f"Error fetching spark data for sensibilidade_juros: {e}")
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
    logger.info("Starting sensibilidade_juros collection...")
    di_res = fetch_yfinance_history(["DI1F27.SA", "B5MB11.SA"])
    di_item = None
    for item in di_res:
        if (
            item.get("response", [{}])[0]
            .get("indicators", {})
            .get("quote", [{}])[0]
            .get("close", [])
        ):
            di_item = item
            break

    if not di_item:
        save_sensibilidade_juros_data(
            SensibilidadeJurosData(
                timestamp=datetime.now(timezone.utc),
                alertas_json="[]",
                fonte=mt5.fonte_efetiva("yfinance"),
            )
        )
        return False

    di_closes = (
        di_item.get("response", [{}])[0]
        .get("indicators", {})
        .get("quote", [{}])[0]
        .get("close", [])
    )
    di_dates = di_item.get("response", [{}])[0].get("timestamp", [])

    d_valid = [(d, c) for d, c in zip(di_dates, di_closes) if c is not None]
    if len(d_valid) < 30:
        save_sensibilidade_juros_data(
            SensibilidadeJurosData(
                timestamp=datetime.now(timezone.utc),
                alertas_json="[]",
                fonte=mt5.fonte_efetiva("yfinance"),
            )
        )
        return False

    d_dates = [x[0] for x in d_valid][-30:]
    d_dict = {x[0]: x[1] for x in d_valid}

    batch_size = 15
    batches = [
        [f"{t}.SA" for t in TICKERS_SENSIVEIS[i : i + batch_size]]
        for i in range(0, len(TICKERS_SENSIVEIS), batch_size)
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
            common_dates = sorted(list(set(d_dates).intersection(set(s_dict.keys()))))

            if len(common_dates) >= 15:
                s_common = [s_dict[d] for d in common_dates]
                d_common = [d_dict[d] for d in common_dates]

                s_returns = calculate_returns(s_common)
                d_returns = calculate_returns(d_common)

                corr = calculate_pearson(s_returns, d_returns)
                if corr < 0:
                    correlations.append({"ticker": symbol, "correlation": corr})

    if not correlations:
        save_sensibilidade_juros_data(
            SensibilidadeJurosData(
                timestamp=datetime.now(timezone.utc),
                alertas_json="[]",
                fonte=mt5.fonte_efetiva("yfinance"),
            )
        )
        return False

    correlations.sort(key=lambda x: x["correlation"])
    negativas = correlations[:3]

    data = SensibilidadeJurosData(
        timestamp=datetime.now(timezone.utc),
        alertas_json=json.dumps(negativas),
        fonte=mt5.fonte_efetiva("yfinance"),
    )
    save_sensibilidade_juros_data(data)
    logger.info("Saved sensibilidade_juros data.")
    return True


if __name__ == "__main__":
    collect_and_save()
