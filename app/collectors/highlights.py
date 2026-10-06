import json
import logging
import os
import sys
from datetime import datetime, timezone

import httpx

from app.database import HighlightsData, save_highlights_data
from app.collectors import mt5
from app.collectors.utils import fetch_with_retry

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# List of highly liquid B3 tickers
TICKERS = [
    "PETR4",
    "VALE3",
    "ITUB4",
    "BBDC4",
    "B3SA3",
    "ABEV3",
    "ELET3",
    "RENT3",
    "WEGE3",
    "BBAS3",
    "ITSA4",
    "SUZB3",
    "BPAC11",
    "RADL3",
    "EQTL3",
    "CSAN3",
    "PRIO3",
    "RDOR3",
    "RAIL3",
    "SBSP3",
    "VIVT3",
    "CMIG4",
    "LREN3",
    "CPLE6",
    "UGPA3",
    "ENEV3",
    "TIMS3",
    "TOTS3",
    "EGIE3",
    "HAPV3",
]


UNIVERSO = 100  # ações mais negociadas do dia que entram no ranking
LISTA_URL = (
    "https://brapi.dev/api/quote/list"
    f"?type=stock&sortBy=volume&sortOrder=desc&limit={UNIVERSO}"
)


def fetch_brapi_lista() -> HighlightsData | None:
    """Uma única requisição ao /api/quote/list da brapi (não exige token).

    O plano gratuito da brapi não aceita vários ativos em /api/quote, e 30
    requisições por coleta estourariam a cota mensal. A listagem traz a
    variação do dia de todas as ações; o ranking usa as UNIVERSO mais
    negociadas, para não premiar papéis sem liquidez.
    """
    token = os.environ.get("BRAPI_TOKEN")
    url = LISTA_URL + (f"&token={token}" if token else "")
    try:
        data = fetch_with_retry(url, timeout=15.0).json()
    except Exception as e:  # noqa: BLE001 - qualquer falha cai no plano B
        logger.error(f"Error fetching brapi quote list: {type(e).__name__}: {e}")
        return None

    ativos = []
    up_count = 0
    down_count = 0
    for item in data.get("stocks") or []:
        change = item.get("change")
        close = item.get("close")
        if change is None or not close or item.get("type") not in (None, "stock"):
            continue
        ativos.append(
            {
                "ticker": item.get("stock", ""),
                "price": float(close),
                "change_percent": float(change),
            }
        )
        if float(change) > 0:
            up_count += 1
        elif float(change) < 0:
            down_count += 1

    if len(ativos) < 10:
        logger.error(f"brapi quote list returned only {len(ativos)} usable stocks")
        return None

    ativos.sort(key=lambda x: x["change_percent"], reverse=True)
    return HighlightsData(
        timestamp=datetime.now(timezone.utc),
        highs_json=json.dumps(ativos[:5]),
        lows_json=json.dumps(sorted(ativos[-5:], key=lambda x: x["change_percent"])),
        fonte="brapi",
        up_count=up_count,
        down_count=down_count,
        total_count=len(ativos),
    )


def fetch_brapi() -> HighlightsData | None:
    BRAPI_TOKEN = os.environ.get("BRAPI_TOKEN")
    if not BRAPI_TOKEN:
        logger.warning("BRAPI_TOKEN not set, skipping brapi.dev for highlights")
        return None

    tickers_str = ",".join(TICKERS)
    url = f"https://brapi.dev/api/quote/{tickers_str}?token={BRAPI_TOKEN}&fundamental=false"

    try:
        response = fetch_with_retry(url, timeout=15.0)
        data = response.json()

        if "results" not in data or not data["results"]:
            logger.error("Invalid response from brapi for highlights")
            return None

        parsed_results = []
        up_count = 0
        down_count = 0
        for result in data["results"]:
            price = result.get("regularMarketPrice")
            prev_close = result.get("regularMarketPreviousClose")

            if price is None or prev_close is None or prev_close == 0:
                continue

            change_percent = ((price - prev_close) / prev_close) * 100

            parsed_results.append(
                {
                    "ticker": result.get("symbol", ""),
                    "price": price,
                    "change_percent": change_percent,
                }
            )
            if change_percent > 0:
                up_count += 1
            elif change_percent < 0:
                down_count += 1

        if not parsed_results:
            return None

        # Sort by change percent
        parsed_results.sort(key=lambda x: x["change_percent"], reverse=True)

        highs = parsed_results[:5]
        lows = parsed_results[-5:]
        lows.sort(
            key=lambda x: x["change_percent"]
        )  # Sort lows ascending (worst first)

        return HighlightsData(
            timestamp=datetime.now(timezone.utc),
            highs_json=json.dumps(highs),
            lows_json=json.dumps(lows),
            fonte="brapi",
            up_count=up_count,
            down_count=down_count,
            total_count=len(parsed_results),
        )
    except httpx.HTTPError as e:
        logger.error(f"Error fetching highlights from brapi: {e}")
        return None


def fetch_yfinance() -> HighlightsData | None:
    parsed_results = []
    up_count = 0
    down_count = 0

    # Batching tickers in groups of 15 to respect URL length and API limits
    batch_size = 15
    batches = [TICKERS[i : i + batch_size] for i in range(0, len(TICKERS), batch_size)]

    with httpx.Client(timeout=10.0) as client:
        for batch in batches:
            symbols = ",".join([f"{t}.SA" for t in batch])
            url = f"https://query1.finance.yahoo.com/v7/finance/spark?symbols={symbols}&range=1d&interval=1d"
            try:
                response = fetch_with_retry(url, client=client)
                data = response.json()

                for item in data.get("spark", {}).get("result", []):
                    if not item.get("response"):
                        continue

                    symbol = item.get("symbol", "").replace(".SA", "")
                    meta = item["response"][0].get("meta", {})
                    price = meta.get("regularMarketPrice")
                    prev_close = meta.get("chartPreviousClose")

                    if price is None or prev_close is None or prev_close == 0:
                        continue

                    change_percent = ((price - prev_close) / prev_close) * 100

                    parsed_results.append(
                        {
                            "ticker": symbol,
                            "price": price,
                            "change_percent": change_percent,
                        }
                    )
                    if change_percent > 0:
                        up_count += 1
                    elif change_percent < 0:
                        down_count += 1
            except httpx.HTTPError as e:
                logger.error(f"Error fetching batch {symbols} from yfinance: {e}")
                continue

    if not parsed_results:
        return None

    parsed_results.sort(key=lambda x: x["change_percent"], reverse=True)

    highs = parsed_results[:5]
    lows = parsed_results[-5:]
    lows.sort(key=lambda x: x["change_percent"])  # Sort lows ascending (worst first)

    return HighlightsData(
        timestamp=datetime.now(timezone.utc),
        highs_json=json.dumps(highs),
        lows_json=json.dumps(lows),
        fonte=mt5.fonte_efetiva("yfinance"),
        up_count=up_count,
        down_count=down_count,
        total_count=len(parsed_results),
    )


def collect_and_save() -> bool:
    logger.info("Starting highlights collection...")
    data = None
    if mt5.configurado():
        # MetaTrader 5 é a fonte preferencial; sem ele, segue a ordem antiga.
        with mt5.exclusivo():
            data = fetch_yfinance()
    if not data:
        data = fetch_brapi_lista()
    if not data:
        logger.info("Falling back highlights to brapi quote by ticker...")
        data = fetch_brapi()
    if not data:
        logger.info("Falling back highlights to yfinance...")
        data = fetch_yfinance()

    if data:
        save_highlights_data(data)
        logger.info("Saved highlights data.")
        return True
    else:
        logger.error("Failed to collect highlights data from all sources.")
        return False


if __name__ == "__main__":
    success = collect_and_save()
    if not success:
        sys.exit(1)
