import json
import logging
from datetime import datetime, timezone

from app.collectors.utils import fetch_with_retry
from app.database import (
    AnomaliaPesoData,
    save_anomalia_peso_data,
    get_latest_ibovespa_data,
)

logger = logging.getLogger(__name__)

PESOS = {
    "VALE3": 12.0,
    "PETR4": 8.0,
    "ITUB4": 8.0,
    "BBDC4": 4.5,
    "B3SA3": 4.0,
}


def collect_and_save() -> bool:
    try:
        ibov_data = get_latest_ibovespa_data()
        if not ibov_data:
            return False
        ibov_prev_close = ibov_data.previous_close

        symbols = [f"{t}.SA" for t in PESOS.keys()]
        url = "https://query1.finance.yahoo.com/v8/finance/spark"
        params = {"symbols": ",".join(symbols), "range": "1d", "interval": "1d"}

        response = fetch_with_retry(url, params=params)

        if not response:
            return False

        json_resp = response.json()

        if "spark" in json_resp:
            result = json_resp.get("spark", {}).get("result", [])
        else:
            result = []
            for sym, data in json_resp.items():
                if isinstance(data, dict) and "symbol" in data:
                    result.append(data)

        if not result:
            return False

        alertas = []
        for item in result:
            if "spark" in json_resp:
                ticker = item.get("symbol", "").replace(".SA", "")
                if ticker not in PESOS:
                    continue
                response_data = item.get("response", [])
                if not response_data:
                    continue
                meta = response_data[0].get("meta", {})
                prev_close = meta.get("chartPreviousClose", meta.get("previousClose"))
                regular_price = meta.get("regularMarketPrice")
            else:
                ticker = item.get("symbol", "").replace(".SA", "")
                if ticker not in PESOS:
                    continue
                prev_close = item.get("chartPreviousClose", item.get("previousClose"))
                close_prices = item.get("close", [])
                regular_price = item.get("fulldayPrice")
                if regular_price is None and close_prices:
                    regular_price = close_prices[-1]

            if prev_close is None or regular_price is None:
                continue

            var_pct = (regular_price - prev_close) / prev_close * 100
            impacto = var_pct * PESOS[ticker] * ibov_prev_close / 10000
            alertas.append({"ticker": ticker, "impacto": impacto})

        if not alertas:
            return False
        alertas.sort(key=lambda x: abs(x["impacto"]), reverse=True)
        top3 = alertas[:3]

        data = AnomaliaPesoData(
            timestamp=datetime.now(timezone.utc),
            alertas_json=json.dumps(top3),
            fonte="yfinance",
        )
        save_anomalia_peso_data(data)
        return True
    except Exception as e:
        logger.exception(f"Erro em anomalia_peso: {e}")
        return False
