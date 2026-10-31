import json
import logging
from datetime import datetime, timezone
from app.database import ConcentracaoOrdensData, save_concentracao_ordens_data
from app.collectors.utils import fetch_with_retry

logger = logging.getLogger(__name__)

TICKERS = [
    "PETR4",
    "VALE3",
    "ITUB4",
    "BBDC4",
    "B3SA3",
    "ABEV3",
    "BBAS3",
    "ELET3",
    "WEGE3",
    "RENT3",
    "SUZB3",
    "JBSS3",
    "RADL3",
    "LREN3",
    "BPAC11",
    "EQTL3",
    "PRIO3",
    "RAIL3",
    "SBSP3",
    "VIVT3",
    "BRFS3",
    "HAPV3",
    "RDOR3",
    "CMIG4",
    "CPLE3",
    "TOTS3",
    "EGIE3",
    "CSAN3",
    "CCRO3",
    "TIMS3",
]


def collect_and_save() -> bool:
    tickers_str = "%2C".join(TICKERS)
    url = f"https://brapi.dev/api/quote/{tickers_str}"
    try:
        response = fetch_with_retry(url)
        data = response.json()
        results = data.get("results", [])
    except Exception as e:
        logger.error(f"Erro ao buscar concentracao de ordens: {e}")
        save_concentracao_ordens_data(
            ConcentracaoOrdensData(
                timestamp=datetime.now(timezone.utc),
                alertas_json="[]",
                fonte="brapi",
            )
        )
        return True

    alertas = []
    for r in results:
        symbol = r.get("symbol")
        volume = r.get("regularMarketVolume", 0) or 0
        price = r.get("regularMarketPrice", 0) or 0
        trades = r.get("regularMarketTrades")
        if trades is None:
            continue
        if trades > 0 and volume > 0 and price > 0:
            vol_financeiro = volume * price
            ticket_medio = vol_financeiro / trades
            alertas.append(
                {
                    "ticker": symbol,
                    "ticket_medio": ticket_medio,
                    "volume_financeiro": vol_financeiro,
                    "trades": trades,
                }
            )

    alertas_ordenados = sorted(alertas, key=lambda x: x["ticket_medio"], reverse=True)[
        :3
    ]
    if not alertas_ordenados:
        logger.info(
            "Nenhuma contagem de trades encontrada na fonte para Concentracao de Ordens."
        )
    save_concentracao_ordens_data(
        ConcentracaoOrdensData(
            timestamp=datetime.now(timezone.utc),
            alertas_json=json.dumps(alertas_ordenados),
            fonte="brapi",
        )
    )
    return True
