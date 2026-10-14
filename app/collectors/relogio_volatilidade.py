import json
import logging
from datetime import datetime, timezone

from app.database import get_connection

logger = logging.getLogger(__name__)


def collect_and_save() -> bool:
    try:
        from app.collectors.utils import fetch_with_retry

        # We need intraday data for ^BVSP
        url = "https://query1.finance.yahoo.com/v8/finance/chart/^BVSP?range=1d&interval=15m"
        data = fetch_with_retry(url)

        if not data:
            return False

        result = data.json().get("chart", {}).get("result", [])
        if not result:
            return False

        quote = result[0].get("indicators", {}).get("quote", [])
        if not quote:
            return False

        highs = quote[0].get("high", [])
        lows = quote[0].get("low", [])

        # Calculate amplitudes
        amplitudes = []
        for h, low in zip(highs, lows):
            if h is not None and low is not None:
                amplitudes.append(h - low)

        if not amplitudes:
            return False

        # Find peak
        max_amp = max(amplitudes)

        alertas = {
            "ticker": "^BVSP",
            "variacao": result[0].get("meta", {}).get("regularMarketPrice", 0)
            - result[0].get("meta", {}).get("previousClose", 0),
            "amplitude_percentual": (
                max_amp / result[0].get("meta", {}).get("previousClose", 1)
            )
            * 100,
            "minima": result[0].get("meta", {}).get("regularMarketDayLow", 0),
            "maxima": result[0].get("meta", {}).get("regularMarketDayHigh", 0),
        }

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM relogio_volatilidade_cache")
        cursor.execute(
            """
            INSERT INTO relogio_volatilidade_cache (timestamp, alertas_json, fonte)
            VALUES (?, ?, ?)
            """,
            (datetime.now(timezone.utc), json.dumps(alertas), "yfinance"),
        )
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error collecting relogio_volatilidade: {e}")
        return False
