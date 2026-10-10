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

# Setor de cada ação da cesta, em português, como o leitor do painel conhece.
# Ações fora deste mapa ficam de fora do cálculo: um grupo "sem setor" não
# pode ser apontado como o setor que lidera o dia.
SETOR_MAP = {
    "PETR4": "Petróleo e gás",
    "PRIO3": "Petróleo e gás",
    "CSAN3": "Petróleo e gás",
    "UGPA3": "Petróleo e gás",
    "VALE3": "Mineração",
    "ITUB4": "Financeiro",
    "BBDC4": "Financeiro",
    "B3SA3": "Financeiro",
    "BBAS3": "Financeiro",
    "ITSA4": "Financeiro",
    "BPAC11": "Financeiro",
    "ABEV3": "Consumo não cíclico",
    "ELET3": "Energia elétrica",
    "EQTL3": "Energia elétrica",
    "CMIG4": "Energia elétrica",
    "CPLE6": "Energia elétrica",
    "ENEV3": "Energia elétrica",
    "EGIE3": "Energia elétrica",
    "SBSP3": "Saneamento",
    "WEGE3": "Bens industriais",
    "SUZB3": "Papel e celulose",
    "RADL3": "Varejo",
    "LREN3": "Varejo",
    "RDOR3": "Saúde",
    "HAPV3": "Saúde",
    "RAIL3": "Transporte e logística",
    "RENT3": "Transporte e logística",
    "VIVT3": "Telecomunicações",
    "TIMS3": "Telecomunicações",
    "TOTS3": "Tecnologia",
}


def fetch_brapi() -> tuple[dict[str, float], dict[str, float]] | None:
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
        volumes = {}
        for item in data["results"]:
            price = item.get("regularMarketPrice")
            prev_close = item.get("regularMarketPreviousClose")
            vol = item.get("regularMarketVolume")

            if price is not None and prev_close is not None and prev_close > 0:
                change = ((price - prev_close) / prev_close) * 100
                variacoes[item["symbol"]] = change
            if price is not None and vol is not None:
                volumes[item["symbol"]] = vol * price

        return (variacoes, volumes) if variacoes else None
    except Exception as e:
        logger.error(f"Erro ao buscar variacoes na brapi: {e}")
        return None


def fetch_yfinance() -> tuple[dict[str, float], dict[str, float]] | None:
    variacoes = {}
    volumes = {}
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

                    vol = meta.get("regularMarketVolume")
                    if price is not None and vol is not None:
                        volumes[symbol] = vol * price
            except Exception as e:
                logger.error(f"Erro ao buscar lote {symbols} no yfinance: {e}")
                continue

    return (variacoes, volumes) if variacoes else None


def collect_and_save() -> bool:
    logger.info("Starting concentracao_setorial collection...")

    dados = None
    fonte = "brapi"

    if mt5.configurado():
        with mt5.exclusivo():
            dados = fetch_yfinance()
            if dados:
                fonte = mt5.fonte_efetiva("yfinance")

    if not dados:
        dados = fetch_brapi()

    if not dados:
        dados = fetch_yfinance()
        fonte = "yfinance"

    if not dados:
        logger.error("Failed to collect concentracao_setorial data from all sources.")
        return False

    variacoes, volumes = dados

    setores_vars = defaultdict(list)
    for ticker, change in variacoes.items():
        setor = SETOR_MAP.get(ticker)
        if setor is None:
            continue
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

    # Guarda o setor de melhor média mesmo quando ela é negativa; a tela só o
    # chama de destaque quando a média é positiva (spec 025, Cálculos).
    melhor_setor = max(media_setores.items(), key=lambda x: x[1])

    setores_vols: dict[str, float] = defaultdict(float)
    for ticker, vol in volumes.items():
        setor = SETOR_MAP.get(ticker)
        if setor is None:
            continue
        setores_vols[setor] += vol

    if setores_vols:
        lider_vol = max(setores_vols.items(), key=lambda x: x[1])
        setor_lider_volume = lider_vol[0]
        volume_lider = lider_vol[1]
    else:
        setor_lider_volume = ""
        volume_lider = 0.0

    data = ConcentracaoSetorialData(
        timestamp=datetime.now(timezone.utc),
        setor_destaque=melhor_setor[0],
        variacao_media=melhor_setor[1],
        fonte=fonte,
        setor_lider_volume=setor_lider_volume,
        volume_lider=volume_lider,
    )

    save_concentracao_setorial_data(data)
    logger.info("Saved concentracao_setorial data.")
    return True
