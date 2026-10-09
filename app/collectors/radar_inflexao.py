import json
import logging
from datetime import datetime, timezone
import yfinance as yf  # type: ignore

from app.database import get_connection

logger = logging.getLogger(__name__)

# Mock list of tickers
TICKERS = [
    "PETR4.SA",
    "VALE3.SA",
    "ITUB4.SA",
    "BBDC4.SA",
    "BBAS3.SA",
    "B3SA3.SA",
    "ABEV3.SA",
    "ELET3.SA",
    "WEGE3.SA",
    "RENT3.SA",
    "SUZB3.SA",
    "ITSA4.SA",
    "EQTL3.SA",
    "RADL3.SA",
    "PRIO3.SA",
    "LREN3.SA",
    "BPAC11.SA",
    "HAPV3.SA",
    "VIVT3.SA",
    "SBSP3.SA",
    "BRFS3.SA",
    "JBSS3.SA",
    "ENEV3.SA",
    "TOTS3.SA",
    "CMIG4.SA",
    "CSNA3.SA",
    "GGBR4.SA",
    "CPLE6.SA",
    "EGIE3.SA",
    "RAIL3.SA",
]


def collect_and_save() -> bool:
    try:
        data = yf.download(
            TICKERS, period="1mo", interval="1d", progress=False, timeout=10
        )
    except Exception as e:
        logger.error(f"Error fetching data from yfinance: {e}")
        return False

    if data.empty:
        return False

    if "Close" in data:
        closes = data["Close"]
    else:
        closes = data

    if len(closes) < 16:  # Need at least D-15 to D0
        return False

    alertas = []

    # We need D-15 to D-1 and D0
    recent_closes = closes.tail(16)
    d_0_series = recent_closes.iloc[-1]
    d_1_series = recent_closes.iloc[-2]
    d_15_series = recent_closes.iloc[0]

    for ticker in TICKERS:
        try:
            d_0 = d_0_series[ticker]
            d_1 = d_1_series[ticker]
            d_15 = d_15_series[ticker]

            if not d_0 or not d_1 or not d_15 or d_1 == 0 or d_15 == 0:
                continue

            retorno_acumulado = ((d_1 - d_15) / d_15) * 100
            variacao_hoje = ((d_0 - d_1) / d_1) * 100

            if retorno_acumulado < -5 and variacao_hoje > 2:
                alertas.append(
                    {
                        "ticker": ticker.replace(".SA", ""),
                        "variacao_hoje": round(variacao_hoje, 2),
                        "retorno_acumulado": round(retorno_acumulado, 2),
                    }
                )
        except KeyError:
            continue

    # Sort by the ones that fell the most
    alertas.sort(key=lambda x: x["retorno_acumulado"])
    top_5 = alertas[:5]

    # Save to database
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS radar_inflexao_cache (
            timestamp TEXT PRIMARY KEY,
            alertas_json TEXT NOT NULL,
            fonte TEXT NOT NULL
        )
    """)
    cursor.execute(
        """
        INSERT INTO radar_inflexao_cache (timestamp, alertas_json, fonte)
        VALUES (?, ?, ?)
    """,
        (datetime.now(timezone.utc).isoformat(), json.dumps(top_5), "yfinance"),
    )
    conn.commit()
    conn.close()

    return True
