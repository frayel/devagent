import logging
from datetime import datetime, timezone
import httpx

from app.collectors.utils import fetch_with_retry
from app.database import ClimaGlobalData, save_clima_global_data

logger = logging.getLogger(__name__)


def fetch_chart(symbol: str) -> dict | None:
    url = f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}?range=2d&interval=1d"
    try:
        response = fetch_with_retry(url)
        return response.json()
    except (httpx.HTTPError, ValueError) as e:
        logger.error("Failed to fetch %s: %s", symbol, e)
        return None


def extract_pct_change(data: dict) -> float | None:
    try:
        result = data["chart"]["result"][0]
        closes = result["indicators"]["quote"][0]["close"]
        valid_closes = [c for c in closes if c is not None]
        if len(valid_closes) < 2:
            # Maybe the market just opened, check prev_close
            meta = result["meta"]
            prev_close = meta.get("chartPreviousClose")
            if not prev_close or len(valid_closes) < 1:
                return None
            current_price = meta.get("regularMarketPrice", valid_closes[-1])
            return ((current_price - prev_close) / prev_close) * 100

        current_price = valid_closes[-1]
        previous_close = valid_closes[-2]
        return ((current_price - previous_close) / previous_close) * 100
    except (KeyError, IndexError, TypeError) as e:
        logger.error("Failed to extract pct change: %s", e)
        return None


def collect_and_save() -> bool:
    es_data = fetch_chart("ES=F")
    vix_data = fetch_chart("^VIX")

    if not es_data or not vix_data:
        logger.warning("Clima Global: Missing data for ES=F or ^VIX")
        return False

    sp500_pct = extract_pct_change(es_data)
    vix_pct = extract_pct_change(vix_data)

    if sp500_pct is None or vix_pct is None:
        logger.warning("Clima Global: Could not extract pct change")
        return False

    status = "Neutro"
    if vix_pct > 3.0 and sp500_pct < -0.5:
        status = "Aversão a Risco"
    elif vix_pct < -2.0 and sp500_pct > 0.5:
        status = "Apetite a Risco"

    data = ClimaGlobalData(
        timestamp=datetime.now(timezone.utc),
        sp500_pct=sp500_pct,
        vix_pct=vix_pct,
        status=status,
        fonte="yfinance",
    )

    save_clima_global_data(data)
    return True
