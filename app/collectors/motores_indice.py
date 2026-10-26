import json
import logging
from datetime import datetime, timezone

import httpx

from app.database import MotoresIndiceData, save_motores_indice_data
from app.collectors.utils import fetch_with_retry

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Grupos de ações para Motores do Índice
MOTORES = {
    "Financeiro": [
        "ITUB4",
        "BBDC4",
        "BBAS3",
        "ITSA4",
        "BPAC11",
        "BBSE3",
        "CXSE3",
        "SANB11",
    ],
    "Commodities": [
        "VALE3",
        "PETR4",
        "PETR3",
        "SUZB3",
        "CSNA3",
        "USIM5",
        "PRIO3",
        "KLBN11",
    ],
    "Doméstico": [
        "WEGE3",
        "RENT3",
        "LREN3",
        "RADL3",
        "EQTL3",
        "SBSP3",
        "CMIG4",
        "TOTS3",
    ],
}


def fetch_yfinance() -> MotoresIndiceData | None:
    motores_resultados: list[dict[str, float | str]] = []

    with httpx.Client(timeout=10.0) as client:
        for nome_motor, tickers in MOTORES.items():
            symbols = ",".join([f"{t}.SA" for t in tickers])
            # Usando spark endpoint para as variações diárias (fechamento atual vs fechamento anterior)
            url = f"https://query1.finance.yahoo.com/v8/finance/spark?symbols={symbols}&range=1d&interval=1d"

            soma_variacao = 0.0
            contador = 0

            try:
                response = fetch_with_retry(url, client=client)
                data = response.json()

                for item in data.get("spark", {}).get("result", []):
                    if not item.get("response"):
                        continue

                    meta = item["response"][0].get("meta", {})
                    price = meta.get("regularMarketPrice")
                    prev_close = meta.get("chartPreviousClose")

                    if price is None or prev_close is None or prev_close == 0:
                        continue

                    change_percent = ((price - prev_close) / prev_close) * 100
                    soma_variacao += change_percent
                    contador += 1
            except httpx.HTTPError as e:
                logger.error(f"Error fetching batch {symbols} for {nome_motor}: {e}")
                continue

            if contador > 0:
                variacao_media = soma_variacao / contador
                motores_resultados.append(
                    {"nome": nome_motor, "variacao": variacao_media}
                )

    if len(motores_resultados) < 3:
        logger.error(
            f"Not all motors fetched successfully, got {len(motores_resultados)}"
        )
        return None

    # Ordenar por variação absoluta decrescente (do maior impacto para o menor)
    motores_resultados.sort(key=lambda x: abs(float(x["variacao"])), reverse=True)

    return MotoresIndiceData(
        timestamp=datetime.now(timezone.utc),
        motores_json=json.dumps(motores_resultados),
        fonte="yfinance",
    )


def collect_and_save() -> bool:
    logger.info("Starting motores_indice collection...")
    data = fetch_yfinance()

    if data:
        save_motores_indice_data(data)
        logger.info("Saved motores_indice data.")
        return True
    else:
        logger.error("Failed to collect motores_indice data.")
        return False


if __name__ == "__main__":
    import sys

    success = collect_and_save()
    if not success:
        sys.exit(1)
