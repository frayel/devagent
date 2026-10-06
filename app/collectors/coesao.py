import logging
from datetime import datetime, timezone

import httpx

from app.database import CoesaoData, save_coesao_data
from app.collectors import mt5
from app.collectors.utils import fetch_with_retry

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Spec: VALE3.SA, PETR4.SA, ITUB4.SA, BBDC4.SA, BBAS3.SA, WEGE3.SA, ABEV3.SA, RENT3.SA, SUZB3.SA, BPAC11.SA
TICKERS = [
    "VALE3.SA",
    "PETR4.SA",
    "ITUB4.SA",
    "BBDC4.SA",
    "BBAS3.SA",
    "WEGE3.SA",
    "ABEV3.SA",
    "RENT3.SA",
    "SUZB3.SA",
    "BPAC11.SA",
]


def fetch_yfinance() -> CoesaoData | None:
    range_str = "1d"

    ibov_url = f"https://query2.finance.yahoo.com/v8/finance/chart/%5EBVSP?range={range_str}&interval=1d"
    try:
        response = fetch_with_retry(ibov_url, timeout=10.0)
        ibov_data = response.json()
        result = ibov_data["chart"]["result"][0]

        # Determine ibov direction
        meta = result["meta"]
        prev_close = meta["chartPreviousClose"]

        closes = result["indicators"]["quote"][0]["close"]
        valid_closes = [c for c in closes if c is not None]
        if not valid_closes:
            logger.warning("No valid closes for ^BVSP")
            return None

        current_close = valid_closes[-1]
        ibov_direction = (
            current_close >= prev_close
        )  # True if positive/neutral, False if negative

    except Exception as e:
        logger.error(f"Error fetching ^BVSP for coesao: {e}")
        return None

    symbols = ",".join(TICKERS)
    url = f"https://query1.finance.yahoo.com/v7/finance/spark?symbols={symbols}&range={range_str}&interval=1d"

    concordantes = 0
    total = len(TICKERS)

    try:
        with httpx.Client(timeout=10.0) as client:
            response = fetch_with_retry(url, client=client)
            data = response.json()

            for item in data.get("spark", {}).get("result", []):
                if not item.get("response"):
                    continue

                meta = item["response"][0]["meta"]
                prev_close = meta.get("chartPreviousClose")
                if prev_close is None:
                    continue

                close_prices = (
                    item["response"][0]
                    .get("indicators", {})
                    .get("quote", [{}])[0]
                    .get("close", [])
                )
                valid_closes = [c for c in close_prices if c is not None]
                if not valid_closes:
                    continue

                current_close = valid_closes[-1]
                stock_direction = current_close >= prev_close

                if stock_direction == ibov_direction:
                    concordantes += 1

    except Exception as e:
        logger.error(f"Error fetching spark data for coesao: {e}")
        return None

    return CoesaoData(
        timestamp=datetime.now(timezone.utc),
        concordantes=concordantes,
        total=total,
        fonte=mt5.fonte_efetiva("yfinance"),
    )


def fetch_brapi() -> CoesaoData | None:
    # We fallback to brapi if yfinance fails
    try:
        import os

        token = os.environ.get("BRAPI_TOKEN")

        # Get ^BVSP
        url_ibov = "https://brapi.dev/api/quote/%5EBVSP"
        if token:
            url_ibov += f"?token={token}"

        res_ibov = fetch_with_retry(url_ibov, timeout=10.0)
        data_ibov = res_ibov.json()

        if not data_ibov.get("results"):
            return None

        ibov_res = data_ibov["results"][0]
        ibov_change = ibov_res.get("regularMarketChange", 0)
        ibov_direction = ibov_change >= 0

        # Get Tickers
        tickers_str = ",".join([t.replace(".SA", "") for t in TICKERS])
        url_tickers = f"https://brapi.dev/api/quote/{tickers_str}"
        if token:
            url_tickers += f"?token={token}"

        res_tickers = fetch_with_retry(url_tickers, timeout=10.0)
        data_tickers = res_tickers.json()

        if not data_tickers.get("results"):
            return None

        concordantes = 0
        total = len(TICKERS)

        for result in data_tickers["results"]:
            change = result.get("regularMarketChange", 0)
            stock_direction = change >= 0
            if stock_direction == ibov_direction:
                concordantes += 1

        return CoesaoData(
            timestamp=datetime.now(timezone.utc),
            concordantes=concordantes,
            total=total,
            fonte="brapi",
        )

    except Exception as e:
        logger.error(f"Error fetching from brapi for coesao: {e}")
        return None


def collect_and_save() -> bool:
    logger.info("Starting coesao collection...")
    data = fetch_yfinance()
    if not data:
        data = fetch_brapi()

    if data:
        save_coesao_data(data)
        logger.info("Saved coesao data.")
        return True

    logger.error("Failed to collect coesao data.")
    return False


if __name__ == "__main__":
    if collect_and_save():
        from app.database import get_latest_coesao_data

        data = get_latest_coesao_data()
        if data:
            print(f"Success! {data.concordantes}/{data.total} using {data.fonte}")
        else:
            print("Failed.")
