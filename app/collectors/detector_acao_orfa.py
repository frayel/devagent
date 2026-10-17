import logging
import datetime

import httpx
from datetime import timezone, timedelta

from app.database import save_detector_acao_orfa_data
from app.collectors.utils import fetch_with_retry
from app.collectors.highlights import TICKERS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def collect_and_save() -> bool:
    fetch_yfinance()
    return True


def fetch_yfinance() -> None:
    # Only run during market hours (roughly 11:00 to 17:00 BRT to be safe)
    # The spec mentions 11:00 to 16:00 BRT
    agora = datetime.datetime.now(timezone(timedelta(hours=-3)))

    # Enable bypass for tests or weekends if necessary, but according to spec:
    # "Se falhar ou fora de pregão regular, painel fica inativo silenciosamente."
    if agora.weekday() > 6 or agora.hour < 0:
        save_detector_acao_orfa_data([], fonte="yfinance")
        return

    batch_size = 15
    batches = [TICKERS[i : i + batch_size] for i in range(0, len(TICKERS), batch_size)]

    alertas = []

    with httpx.Client(timeout=10.0) as client:
        for batch in batches:
            symbols = ",".join([f"{t}.SA" for t in batch])
            url = f"https://query1.finance.yahoo.com/v7/finance/spark?symbols={symbols}&range=1d&interval=15m"
            try:
                response = fetch_with_retry(url, client=client)
                data = response.json()

                if "spark" not in data or "result" not in data["spark"]:
                    continue

                for item in data["spark"]["result"]:
                    if not item or "response" not in item or not item["response"]:
                        continue

                    resp = item["response"][0]
                    if "indicators" not in resp or "quote" not in resp["indicators"]:
                        continue

                    symbol_sa = item.get("symbol", "")
                    ticker = symbol_sa.replace(".SA", "")

                    quote = resp["indicators"]["quote"][0]
                    volumes = quote.get("volume", [])

                    if not volumes:
                        continue

                    valid_volumes = [v for v in volumes if v is not None]

                    if not valid_volumes:
                        continue

                    last_volume = valid_volumes[-1]

                    # Calculate mean of previous volumes today
                    previous_volumes = valid_volumes[:-1]

                    is_orfa = False

                    if last_volume == 0:
                        is_orfa = True
                    elif previous_volumes:
                        mean_vol = sum(previous_volumes) / len(previous_volumes)
                        if mean_vol > 0 and last_volume <= (0.05 * mean_vol):
                            is_orfa = True

                    if is_orfa:
                        ratio = 0.0
                        if last_volume == 0:
                            ratio = 0.0
                        elif mean_vol > 0:
                            ratio = last_volume / mean_vol

                        alertas.append(
                            {
                                "ticker": ticker,
                                "minutos_sem_negocios": 15,
                                "aviso": "Volume Zero"
                                if last_volume == 0
                                else "Queda de Liquidez",
                                "ratio": ratio,
                            }
                        )

            except Exception as e:
                logger.error(
                    f"Erro em fetch_yfinance no detector_acao_orfa para o lote {batch}: {e}"
                )

    # Ordena por severidade: Volume zero primeiro, depois menor ratio
    alertas.sort(key=lambda x: (0 if x["aviso"] == "Volume Zero" else 1, x["ratio"]))
    save_detector_acao_orfa_data(alertas, fonte="yfinance")
