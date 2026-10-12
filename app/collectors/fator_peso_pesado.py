import json
import logging
from datetime import datetime, timezone
import httpx

from app.database import FatorPesoPesadoData, save_fator_peso_pesado_data
from app.collectors.utils import fetch_with_retry

logger = logging.getLogger(__name__)

TICKERS_PESO = {
    "VALE3.SA": 12.0,
    "PETR4.SA": 8.0,
    "ITUB4.SA": 7.0,
    "PETR3.SA": 4.0,
    "BBAS3.SA": 3.0,
}


def _parse_chart(data: dict) -> dict:
    if "chart" in data and "result" in data["chart"] and data["chart"]["result"]:
        result = data["chart"]["result"][0]
        meta = result["meta"]
        return {
            "current_price": meta.get("regularMarketPrice"),
            "previous_close": meta.get("chartPreviousClose"),
        }
    return {}


def collect_and_save() -> bool:
    try:
        # Fetch IBOV
        ibov_url = "https://query1.finance.yahoo.com/v8/finance/chart/^BVSP?range=1d&interval=1d"
        ibov_resp = fetch_with_retry(ibov_url, timeout=10.0)

        ibov_data = _parse_chart(ibov_resp.json())

        if (
            not ibov_data
            or "current_price" not in ibov_data
            or "previous_close" not in ibov_data
        ):
            logger.warning("Fator Peso Pesado: IBOV missing price data")
            return False

        ibov_current = ibov_data["current_price"]
        ibov_prev = ibov_data["previous_close"]
        ibov_var_pts = ibov_current - ibov_prev
        ibov_var_pct = (ibov_var_pts / ibov_prev) * 100 if ibov_prev else 0

        if abs(ibov_var_pct) < 0.1:
            save_fator_peso_pesado_data(
                FatorPesoPesadoData(
                    timestamp=datetime.now(timezone.utc),
                    proporcao=0.0,
                    mercado_lateral=True,
                    resumo_json=json.dumps({}),
                    fonte="yfinance",
                )
            )
            return True

        # Fetch individual tickers
        contrib_pts = 0.0
        details = {}
        for idx, (ticker, weight) in enumerate(TICKERS_PESO.items()):
            subdomain = "query1" if idx % 2 == 0 else "query2"
            url = f"https://{subdomain}.finance.yahoo.com/v8/finance/chart/{ticker}?range=1d&interval=1d"
            try:
                resp = fetch_with_retry(url, timeout=10.0)
                data = _parse_chart(resp.json())

                if data and "current_price" in data and "previous_close" in data:
                    curr = data["current_price"]
                    prev = data["previous_close"]
                    var_pct = ((curr - prev) / prev * 100) if prev else 0.0

                    # Contribuição em pontos teóricos: (var % * peso / 100) * IBOV anterior
                    pts = (var_pct * weight / 100) * ibov_prev
                    contrib_pts += pts
                    details[ticker] = {"var_pct": var_pct, "contrib_pts": pts}
                else:
                    logger.warning("Fator Peso Pesado: Missing data for %s", ticker)
                    return False
            except Exception as e:
                logger.warning("Fator Peso Pesado: Failed to fetch %s: %s", ticker, e)
                return False

        proporcao = (contrib_pts / ibov_var_pts) * 100 if ibov_var_pts else 0.0

        if proporcao > 500.0:
            proporcao = 500.0
        elif proporcao < -500.0:
            proporcao = -500.0

        save_fator_peso_pesado_data(
            FatorPesoPesadoData(
                timestamp=datetime.now(timezone.utc),
                proporcao=proporcao,
                mercado_lateral=False,
                resumo_json=json.dumps(details),
                fonte="yfinance",
            )
        )

        return True
    except httpx.HTTPError as e:
        logger.warning("Fator Peso Pesado: HTTP error: %s", e)
        return False
    except Exception as e:
        logger.exception("Fator Peso Pesado: Unexpected error: %s", e)
        return False
