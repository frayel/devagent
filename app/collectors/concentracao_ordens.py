"""Termômetro de Concentração de Ordens (spec 058).

Ticket médio = volume financeiro do dia / número de negócios do dia.

O número de negócios vem do MetaTrader 5: a ponte (`mt5.py`) expõe o
`tick_volume` da barra diária, que na B3 conta os negócios, como
`regularMarketTrades`. O Yahoo não traz esse dado, então não há recurso a ele.
"""

import json
import logging
from datetime import datetime, timezone

import httpx

from app.collectors import mt5
from app.collectors.utils import fetch_with_retry
from app.database import ConcentracaoOrdensData, save_concentracao_ordens_data

logger = logging.getLogger(__name__)

TICKERS = [
    "PETR4",
    "VALE3",
    "ITUB4",
    "BBDC4",
    "B3SA3",
    "ABEV3",
    "BBAS3",
    "BBDC3",
    "WEGE3",
    "RENT3",
    "SUZB3",
    "RADL3",
    "LREN3",
    "BPAC11",
    "EQTL3",
    "PRIO3",
    "RAIL3",
    "SBSP3",
    "VIVT3",
    "MBRF3",
    "HAPV3",
    "RDOR3",
    "CMIG4",
    "CPLE3",
    "TOTS3",
    "EGIE3",
    "CSAN3",
    "MOTV3",
    "TIMS3",
]


LOTE = 15
SPARK = (
    "https://query1.finance.yahoo.com/v8/finance/spark?symbols={}&range=1d&interval=1d"
)


def fetch_mt5() -> list[dict] | None:
    """Cotações do dia com número de negócios, servidas só pelo MT5."""
    if not mt5.configurado():
        return None
    resultados: list[dict] = []
    with mt5.exclusivo():
        for i in range(0, len(TICKERS), LOTE):
            simbolos = ",".join(f"{t}.SA" for t in TICKERS[i : i + LOTE])
            try:
                dados = fetch_with_retry(SPARK.format(simbolos)).json()
            except (httpx.HTTPError, ValueError) as e:
                logger.error("Concentração de ordens: MT5 falhou: %s", e)
                continue
            for item in dados.get("spark", {}).get("result", []):
                if not item.get("response"):
                    continue
                meta = item["response"][0].get("meta", {})
                resultados.append(
                    {
                        "symbol": item.get("symbol", "").replace(".SA", ""),
                        "regularMarketVolume": meta.get("regularMarketVolume"),
                        "regularMarketPrice": meta.get("regularMarketPrice"),
                        "regularMarketTrades": meta.get("regularMarketTrades"),
                    }
                )
    return resultados or None


def calcular(results: list[dict]) -> list[dict]:
    alertas = []
    for r in results:
        volume = r.get("regularMarketVolume") or 0
        price = r.get("regularMarketPrice") or 0
        trades = r.get("regularMarketTrades")
        if not trades or volume <= 0 or price <= 0:
            continue
        vol_financeiro = volume * price
        alertas.append(
            {
                "ticker": r.get("symbol"),
                "ticket_medio": vol_financeiro / trades,
                "volume_financeiro": vol_financeiro,
                "trades": trades,
            }
        )
    return sorted(alertas, key=lambda x: x["ticket_medio"], reverse=True)[:3]


def collect_and_save() -> bool:
    alertas = calcular(fetch_mt5() or [])
    if not alertas:
        logger.info(
            "Nenhuma contagem de negócios na fonte para Concentração de Ordens."
        )
    save_concentracao_ordens_data(
        ConcentracaoOrdensData(
            timestamp=datetime.now(timezone.utc),
            alertas_json=json.dumps(alertas),
            fonte="mt5",
        )
    )
    return True
