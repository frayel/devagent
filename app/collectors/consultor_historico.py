import logging
import httpx

from app.consultor.universo import CARTEIRA_IBOVESPA
from app.collectors.utils import fetch_historico_diario_yfinance_chart

logger = logging.getLogger(__name__)

# Série diária de 2 anos: renovar a cada hora basta para as regras e poupa o
# Yahoo de ~90 pedidos a cada rodada de coleta.
REFRESCO = 60


def collect_and_save() -> bool:
    ativos = CARTEIRA_IBOVESPA + ["^BVSP"]
    range_str = "2y"
    interval = "1d"

    sucesso = False

    with httpx.Client() as client:
        for ticker in ativos:
            symbol = ticker.replace(".SA", "")
            try:
                data = fetch_historico_diario_yfinance_chart(
                    symbol, range_str, interval, client, max_age_minutes=REFRESCO
                )
                if data:
                    sucesso = True
            except Exception as e:
                logger.error(f"Erro ao buscar histórico de 2y para {ticker}: {e}")

    return sucesso
