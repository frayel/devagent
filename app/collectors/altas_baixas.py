import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any

import httpx

from app.database import AltasBaixasData, save_altas_baixas_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# A basket of highly liquid B3 tickers to monitor for top gainers/losers
TICKERS = [
    "PETR4",
    "VALE3",
    "ITUB4",
    "BBDC4",
    "ABEV3",
    "BBAS3",
    "B3SA3",
    "WEGE3",
    "RENT3",
    "SUZB3",
    "EQTL3",
    "RADL3",
    "LREN3",
    "PRIO3",
    "ELET3",
    "JBSS3",
    "RAIL3",
    "HAPV3",
    "SBSP3",
    "VIVT3",
]


def extract_top_altas_baixas(
    results: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]] | None:
    valid_results = []
    for r in results:
        price = r.get("regularMarketPrice")
        prev_close = r.get("regularMarketPreviousClose")
        if price is not None and prev_close is not None and prev_close > 0:
            variation = price - prev_close
            variation_percent = (variation / prev_close) * 100
            valid_results.append(
                {
                    "ticker": r["symbol"],
                    "price": price,
                    "variation_percent": variation_percent,
                }
            )

    if not valid_results:
        return None

    valid_results.sort(key=lambda x: x["variation_percent"], reverse=True)

    top_altas = valid_results[:5]
    top_baixas = valid_results[-5:]
    top_baixas.reverse()  # Most negative first

    return top_altas, top_baixas


def fetch_brapi() -> AltasBaixasData | None:
    BRAPI_TOKEN = os.environ.get("BRAPI_TOKEN")
    if not BRAPI_TOKEN:
        logger.warning("BRAPI_TOKEN not set, skipping brapi.dev")
        return None

    tickers_str = ",".join(TICKERS)
    url = f"https://brapi.dev/api/quote/{tickers_str}?token={BRAPI_TOKEN}&fundamental=false"

    try:
        response = httpx.get(url, timeout=10.0)
        response.raise_for_status()
        data = response.json()

        if "results" not in data or not data["results"]:
            logger.error("Invalid response from brapi")
            return None

        tops = extract_top_altas_baixas(data["results"])
        if not tops:
            return None

        top_altas, top_baixas = tops

        return AltasBaixasData(
            timestamp=datetime.now(timezone.utc),
            top_altas_json=json.dumps(top_altas),
            top_baixas_json=json.dumps(top_baixas),
            source="brapi.dev",
        )
    except httpx.HTTPError as e:
        logger.error(f"Error fetching from brapi: {e}")
        return None


def fetch_yfinance() -> AltasBaixasData | None:
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) B3Panel/1.0"}
    results = []

    for ticker in TICKERS:
        url = f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}.SA?range=1d&interval=1d"
        try:
            response = httpx.get(url, headers=headers, timeout=5.0)
            if response.status_code != 200:
                continue

            data = response.json()
            if (
                "chart" not in data
                or "result" not in data["chart"]
                or not data["chart"]["result"]
            ):
                continue

            result = data["chart"]["result"][0]
            meta = result.get("meta", {})
            current_price = meta.get("regularMarketPrice")
            previous_close = meta.get("chartPreviousClose")

            if current_price is not None and previous_close is not None:
                results.append(
                    {
                        "symbol": ticker,
                        "regularMarketPrice": current_price,
                        "regularMarketPreviousClose": previous_close,
                    }
                )

        except httpx.HTTPError as e:
            logger.warning(f"Error fetching {ticker} from yfinance: {e}")
            continue

    if not results:
        return None

    tops = extract_top_altas_baixas(results)
    if not tops:
        return None

    top_altas, top_baixas = tops

    return AltasBaixasData(
        timestamp=datetime.now(timezone.utc),
        top_altas_json=json.dumps(top_altas),
        top_baixas_json=json.dumps(top_baixas),
        source="Yahoo Finance",
    )


def collect_and_save() -> bool:
    logger.info("Starting collection of Altas/Baixas...")
    data = fetch_brapi()
    if not data:
        logger.info("Falling back to yfinance for Altas/Baixas...")
        data = fetch_yfinance()

    if data:
        save_altas_baixas_data(data)
        logger.info(f"Saved Altas/Baixas data from {data.source}.")
        return True
    else:
        logger.error("Failed to collect Altas/Baixas data from all sources.")
        return False


if __name__ == "__main__":
    success = collect_and_save()
    if not success:
        sys.exit(1)
