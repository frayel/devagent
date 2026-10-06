import logging
import os
from datetime import datetime, timezone
from collections import defaultdict
import httpx

from app.database import ConcentracaoSetorialData, save_concentracao_setorial_data
from app.collectors.utils import fetch_with_retry
from app.collectors import mt5
from app.collectors.highlights import TICKERS

logger = logging.getLogger(__name__)

# Mapeamento estático baseado na API da brapi.dev
SETOR_MAP = {
    "PETR4": "Energy Minerals",
    "VALE3": "Non-Energy Minerals",
    "ITUB4": "Finance",
    "BBDC4": "Finance",
    "B3SA3": "Finance",
    "ABEV3": "Consumer Non-Durables",
    "ELET3": "Utilities",
    "RENT3": "Finance",
    "WEGE3": "Producer Manufacturing",
    "BBAS3": "Finance",
    "ITSA4": "Finance",
    "SUZB3": "Process Industries",
    "BPAC11": "Finance",
    "RADL3": "Retail Trade",
    "EQTL3": "Utilities",
    "CSAN3": "Utilities",
    "PRIO3": "Energy Minerals",
    "RDOR3": "Health Services",
    "RAIL3": "Transportation",
    "SBSP3": "Utilities",
    "VIVT3": "Communications",
    "CMIG4": "Utilities",
    "LREN3": "Retail Trade",
    "CPLE6": "Utilities",
    "UGPA3": "Retail Trade",
    "ENEV3": "Utilities",
    "TIMS3": "Communications",
    "TOTS3": "Technology Services",
    "EGIE3": "Utilities",
    "HAPV3": "Health Services",
}


def fetch_brapi() -> dict[str, float] | None:
    token = os.environ.get("BRAPI_TOKEN")
    if not token:
        return None

    tickers_str = ",".join(TICKERS)
    url = f"https://brapi.dev/api/quote/{tickers_str}?token={token}&fundamental=false"

    try:
        response = fetch_with_retry(url, timeout=15.0)
        data = response.json()

        if "results" not in data or not data["results"]:
            return None

        variacoes = {}
        for item in data["results"]:
            price = item.get("regularMarketPrice")
            prev_close = item.get("regularMarketPreviousClose")

            if price is not None and prev_close is not None and prev_close > 0:
                change = ((price - prev_close) / prev_close) * 100
                variacoes[item["symbol"]] = change

        return variacoes
    except Exception as e:
        logger.error(f"Erro ao buscar variacoes na brapi: {e}")
        return None


def fetch_yfinance() -> dict[str, float] | None:
    variacoes = {}
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

                    if price is not None and prev_close is not None and prev_close > 0:
                        change = ((price - prev_close) / prev_close) * 100
                        variacoes[symbol] = change
            except Exception as e:
                logger.error(f"Erro ao buscar lote {symbols} no yfinance: {e}")
                continue

    return variacoes if variacoes else None


def collect_and_save() -> bool:
    logger.info("Starting concentracao_setorial collection...")

    variacoes = None
    fonte = "brapi"

    if mt5.configurado():
        with mt5.exclusivo():
            variacoes = fetch_yfinance()
            if variacoes:
                fonte = mt5.fonte_efetiva("yfinance")

    if not variacoes:
        variacoes = fetch_brapi()

    if not variacoes:
        variacoes = fetch_yfinance()
        fonte = "yfinance"

    if not variacoes:
        logger.error("Failed to collect concentracao_setorial data from all sources.")
        return False

    setores_vars = defaultdict(list)
    for ticker, change in variacoes.items():
        setor = SETOR_MAP.get(ticker, "Unknown")
        setores_vars[setor].append(change)

    media_setores = {}
    for setor, changes in setores_vars.items():
        if changes:
            media_setores[setor] = sum(changes) / len(changes)

    if not media_setores:
        logger.warning(
            "Nenhum dado valido de variacao setorial para calcular a concentracao."
        )
        return False

    melhor_setor = max(media_setores.items(), key=lambda x: x[1])

    data = ConcentracaoSetorialData(
        timestamp=datetime.now(timezone.utc),
        setor_destaque=melhor_setor[0],
        variacao_media=melhor_setor[1],
        fonte=fonte,
    )

    save_concentracao_setorial_data(data)
    logger.info("Saved concentracao_setorial data.")
    return True
