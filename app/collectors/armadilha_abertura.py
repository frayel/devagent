import json
import logging
from datetime import datetime, timezone

from app.collectors.highlights import TICKERS
from app.collectors.utils import fetch_with_retry
from app.database import ArmadilhaAberturaData, save_armadilha_abertura_data

logger = logging.getLogger(__name__)


def collect_and_save() -> bool:
    alertas = []

    tickers_str = ",".join([f"{t}.SA" for t in TICKERS])
    url = f"https://query1.finance.yahoo.com/v7/finance/spark?symbols={tickers_str}&range=2d&interval=1d"

    try:
        resp = fetch_with_retry(url)
        data = resp.json()

        for result in data.get("spark", {}).get("result", []):
            symbol = result.get("symbol", "").replace(".SA", "")
            resp_data = result.get("response", [{}])[0]
            indicators = resp_data.get("indicators", {}).get("quote", [{}])[0]

            closes = indicators.get("close", [])
            opens = indicators.get("open", [])
            highs = indicators.get("high", [])

            if not closes or not opens or not highs or len(closes) < 2:
                continue

            high_ontem = highs[-2]
            close_ontem = closes[-2]
            open_hoje = opens[-1]
            close_hoje = closes[-1]

            if (
                high_ontem is None
                or close_ontem is None
                or open_hoje is None
                or close_hoje is None
            ):
                continue

            if high_ontem > 0 and (open_hoje - high_ontem) / high_ontem > 0.01:
                if close_hoje < close_ontem:
                    alertas.append(
                        {"ticker": symbol, "preco_atual": round(close_hoje, 2)}
                    )

        alertas = alertas[:3]

    except Exception as e:
        logger.error(f"Falha ao coletar armadilha_abertura no yfinance: {e}")
        return False

    save_armadilha_abertura_data(
        ArmadilhaAberturaData(
            timestamp=datetime.now(timezone.utc),
            alertas_json=json.dumps(alertas),
            fonte="yfinance",
        )
    )
    return True
