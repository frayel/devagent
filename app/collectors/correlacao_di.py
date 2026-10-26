import logging
from datetime import datetime, timezone

from app.database import CorrelacaoDIData, save_correlacao_di_data
from app.collectors import mt5
from app.collectors.utils import fetch_with_retry

logger = logging.getLogger(__name__)


def fetch_yfinance_history(
    tickers: list[str], range_str="5d", interval="15m"
) -> list[dict]:
    symbols = ",".join(tickers)
    url = f"https://query1.finance.yahoo.com/v8/finance/spark?symbols={symbols}&range={range_str}&interval={interval}"
    try:
        response = fetch_with_retry(url, timeout=15.0)
        data = response.json()
        return data.get("spark", {}).get("result", [])
    except Exception as e:
        logger.error(f"Error fetching spark data for correlacao_di: {e}")
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
    import math

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
    logger.info("Starting correlacao_di collection...")
    # Tenta pegar os dois tickers pra garantir. Se D1F27 falhar, F29.
    res = fetch_yfinance_history(["DI1F27.SA", "DI1F29.SA", "^BVSP"], "5d", "1d")

    ibov_data = next((x for x in res if x.get("symbol") == "^BVSP"), None)
    di_data = next((x for x in res if x.get("symbol") == "DI1F27.SA"), None)

    if not di_data or not di_data.get("response"):
        di_data = next((x for x in res if x.get("symbol") == "DI1F29.SA"), None)

    if not ibov_data or not di_data:
        save_correlacao_di_data(
            CorrelacaoDIData(
                timestamp=datetime.now(timezone.utc),
                correlacao_intradiaria=0.0,
                correlacao_5d=0.0,
                fonte=mt5.fonte_efetiva("yfinance"),
            )
        )
        return False

    try:
        ibov_closes = ibov_data["response"][0]["indicators"]["quote"][0]["close"]
        ibov_dates = ibov_data["response"][0]["timestamp"]
        di_closes = di_data["response"][0]["indicators"]["quote"][0]["close"]
        di_dates = di_data["response"][0]["timestamp"]

        # 5d correlation
        i_dict_5d = {d: c for d, c in zip(ibov_dates, ibov_closes) if c is not None}
        d_dict_5d = {d: c for d, c in zip(di_dates, di_closes) if c is not None}

        common_dates_5d = sorted(
            list(set(i_dict_5d.keys()).intersection(set(d_dict_5d.keys())))
        )

        corr_5d = 0.0
        if len(common_dates_5d) >= 3:
            i_common = [i_dict_5d[d] for d in common_dates_5d]
            d_common = [d_dict_5d[d] for d in common_dates_5d]
            corr_5d = calculate_pearson(
                calculate_returns(i_common), calculate_returns(d_common)
            )

        # Intraday correlation (15m of today)
        res_intra = fetch_yfinance_history(
            ["DI1F27.SA", "DI1F29.SA", "^BVSP"], "1d", "15m"
        )
        ibov_data_intra = next(
            (x for x in res_intra if x.get("symbol") == "^BVSP"), None
        )
        di_data_intra = next(
            (x for x in res_intra if x.get("symbol") == "DI1F27.SA"), None
        )
        if not di_data_intra or not di_data_intra.get("response"):
            di_data_intra = next(
                (x for x in res_intra if x.get("symbol") == "DI1F29.SA"), None
            )

        corr_intra = 0.0
        if (
            ibov_data_intra
            and di_data_intra
            and ibov_data_intra.get("response")
            and di_data_intra.get("response")
        ):
            ibov_closes_i = ibov_data_intra["response"][0]["indicators"]["quote"][0][
                "close"
            ]
            ibov_dates_i = ibov_data_intra["response"][0]["timestamp"]
            di_closes_i = di_data_intra["response"][0]["indicators"]["quote"][0][
                "close"
            ]
            di_dates_i = di_data_intra["response"][0]["timestamp"]

            i_dict_i = {
                d: c for d, c in zip(ibov_dates_i, ibov_closes_i) if c is not None
            }
            d_dict_i = {d: c for d, c in zip(di_dates_i, di_closes_i) if c is not None}

            common_dates_i = sorted(
                list(set(i_dict_i.keys()).intersection(set(d_dict_i.keys())))
            )
            if len(common_dates_i) >= 5:
                i_common_i = [i_dict_i[d] for d in common_dates_i]
                d_common_i = [d_dict_i[d] for d in common_dates_i]
                corr_intra = calculate_pearson(
                    calculate_returns(i_common_i), calculate_returns(d_common_i)
                )

        data = CorrelacaoDIData(
            timestamp=datetime.now(timezone.utc),
            correlacao_intradiaria=corr_intra,
            correlacao_5d=corr_5d,
            fonte=mt5.fonte_efetiva("yfinance"),
        )
        save_correlacao_di_data(data)
        logger.info("Saved correlacao_di data.")
        return True
    except Exception as e:
        logger.error(f"Failed to process correlacao_di data: {e}")
        return False


if __name__ == "__main__":
    collect_and_save()
