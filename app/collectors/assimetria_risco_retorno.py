import json
import logging
from datetime import datetime, timezone
import httpx

from app.database import AssimetriaRiscoRetornoData, save_assimetria_risco_retorno_data
from app.collectors.utils import fetch_historico_diario_yfinance_spark
from app.collectors import mt5

logger = logging.getLogger(__name__)

TICKERS = [
    "PETR4",
    "VALE3",
    "ITUB4",
    "BBDC4",
    "BBAS3",
    "B3SA3",
    "ABEV3",
    "WEGE3",
    "RENT3",
    "SUZB3",
    "BPAC11",
    "EQTL3",
    "RADL3",
    "PRIO3",
    "SBSP3",
    "GGBR4",
    "RDOR3",
    "RAIL3",
    "VIVT3",
    "BBSE3",
    "JBSS3",
    "ELET3",
    "CPLE6",
    "BRFS3",
    "ENEV3",
    "TIMS3",
    "CMIG4",
    "CCRO3",
    "TOTS3",
    "EGIE3",
    "SOMA3",
    "LREN3",
    "CSAN3",
    "ALOS3",
    "CPFE3",
]


def collect_and_save() -> bool:
    try:
        client = httpx.Client(timeout=10.0)

        history = fetch_historico_diario_yfinance_spark(TICKERS, "3mo", "1d", client)

        alertas = []

        for item in history:
            symbol = item.get("symbol", "").replace(".SA", "")
            closes = item.get("indicators", {}).get("quote", [{}])[0].get("close", [])

            valid_closes = [c for c in closes if c is not None]

            if len(valid_closes) < 30:
                continue

            closes_30 = valid_closes[-30:]
            atual = closes_30[-1]
            min_30 = min(closes_30)
            max_30 = max(closes_30)

            if min_30 <= 0 or atual <= 0:
                continue

            dist_min = (atual - min_30) / min_30
            dist_max = (max_30 - atual) / atual

            if dist_min <= 0.02 and dist_max >= 0.10:
                alertas.append(
                    {
                        "ticker": symbol,
                        "dist_min_pct": round(dist_min * 100, 2),
                        "dist_max_pct": round(dist_max * 100, 2),
                    }
                )

        alertas.sort(key=lambda x: x["dist_min_pct"])

        top_3 = alertas[:3]

        data = AssimetriaRiscoRetornoData(
            timestamp=datetime.now(timezone.utc),
            alertas_json=json.dumps(top_3),
            fonte=mt5.fonte_efetiva("yfinance"),
        )

        save_assimetria_risco_retorno_data(data)
        logger.info(f"Salvo {len(top_3)} alertas de assimetria risco retorno.")
        return True
    except Exception as e:
        logger.error(f"Erro em assimetria_risco_retorno: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    import sys

    success = collect_and_save()
    if not success:
        sys.exit(1)
