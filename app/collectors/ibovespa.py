import json
import logging
import sys
import time
from datetime import datetime, timezone, timedelta

import httpx

from app.database import IbovespaData, save_ibovespa_data
from app.collectors import mt5
from app.collectors.utils import fetch_with_retry

logger = logging.getLogger(__name__)

# Variação diária acima disto é tratada como dado errado da fonte e descartada.
# Era 12%: em 29/10/2026 o Ibovespa variou 15,99% de verdade, com os limites
# do circuit breaker da B3 estendidos naquele dia, e o coletor descartou o
# dado das duas fontes.
VARIACAO_DIARIA_MAXIMA = 20.0  # %

# Limiares de sinal de revisão (Spec 134)
LIMIAR_PCT_REVISAO = 3.0  # % estrito (|pct| > 3.0)
LIMIAR_PONTOS_REVISAO = 5000.0  # pts inclusive (|pts| >= 5000.0)


def calc_mm(closes: list[float], window: int) -> float | None:
    if len(closes) < window:
        return None
    return sum(closes[-window:]) / window


def fetch_yfinance() -> IbovespaData | None:
    url = "https://query2.finance.yahoo.com/v8/finance/chart/^BVSP?range=1y&interval=1d"
    try:
        response = fetch_with_retry(url, timeout=10.0)
        data = response.json()

        result = data["chart"]["result"][0]
        meta = result["meta"]
        current_price = float(meta.get("regularMarketPrice", 0.0))

        timestamps = result["timestamp"]
        closes = result["indicators"]["quote"][0]["close"]

        dates = [
            datetime.fromtimestamp(t, tz=timezone.utc).strftime("%Y-%m-%d")
            for t in timestamps
        ]

        # filter out None closes
        valid_history = [(d, c) for d, c in zip(dates, closes) if c is not None]
        valid_dates = [v[0] for v in valid_history]
        valid_closes = [v[1] for v in valid_history]

        # Regras de fechamento anterior (Spec 134):
        # 1. Série válida com >= 2 fechamentos, e última barra é de hoje (BRT) ou preço atual igual ao último (tol 0,01%):
        #    previous_close = fechamentos[-2]
        # 2. Série com >= 2 fechamentos cuja última barra é de pregão anterior e preço atual difere (antes da abertura):
        #    previous_close = fechamentos[-1]
        # 3. Série com menos de 2 fechamentos: meta["previousClose"], depois meta["regularMarketPreviousClose"]
        # 4. Fallback se ausente: preço atual, com aviso no log (variação 0)
        # `chartPreviousClose` não entra em nenhum passo pois refere-se ao início da janela (1 ano atrás).
        current_date_str = (
            datetime.now(timezone.utc)
            .astimezone(timezone(timedelta(hours=-3)))
            .strftime("%Y-%m-%d")
        )

        previous_close: float | None = None

        if len(valid_closes) >= 2:
            is_hoje = valid_dates[-1] == current_date_str
            is_igual_ultimo = (
                current_price > 0
                and abs(current_price - valid_closes[-1]) / valid_closes[-1] < 0.0001
            )
            if is_hoje or is_igual_ultimo:
                previous_close = float(valid_closes[-2])
            else:
                previous_close = float(valid_closes[-1])
        else:
            meta_prev = meta.get("previousClose") or meta.get(
                "regularMarketPreviousClose"
            )
            if meta_prev is not None:
                previous_close = float(meta_prev)
            else:
                logger.warning(
                    "previous_close ausente em meta e série; usando current_price como fallback."
                )
                previous_close = float(current_price)

        previous_close = float(previous_close) if previous_close is not None else 0.0

        calc_closes = valid_closes.copy()
        if current_price and (not calc_closes or current_price != calc_closes[-1]):
            calc_closes.append(current_price)

        mm21 = calc_mm(calc_closes, 21)
        mm200 = calc_mm(calc_closes, 200)

        if previous_close:
            var_pct = ((current_price - previous_close) / previous_close) * 100
            if abs(var_pct) > VARIACAO_DIARIA_MAXIMA:
                logger.error(f"yfinance returned implausible variation: {var_pct:.2f}%")
                return None

        history_json = json.dumps(
            {"dates": valid_dates[-30:], "closes": valid_closes[-30:]}
        )

        return IbovespaData(
            timestamp=datetime.now(timezone.utc),
            current_price=current_price,
            previous_close=previous_close,
            history_json=history_json,
            fonte=mt5.fonte_efetiva("yfinance"),
            mm21=mm21,
            mm200=mm200,
        )
    except httpx.HTTPError as e:
        logger.error(f"Error fetching from yfinance: {e}")
        return None


def collect_and_save() -> bool:
    logger.info("Starting collection...")
    data = None
    if mt5.configurado():
        # MetaTrader 5 é a fonte preferencial; sem ele, segue a ordem antiga.
        with mt5.exclusivo():
            data = fetch_yfinance()
    if not data:
        logger.info("Falling back to yfinance...")
        data = fetch_yfinance()

    if data:
        # Tenta salvar com retries para tolerar inicialização/aquecimento transitório do banco
        for tentativa in range(3):
            try:
                save_ibovespa_data(data)
                logger.info(f"Saved Ibovespa data. Price: {data.current_price}")
                return True
            except Exception as e:
                logger.warning(
                    f"Falha ao salvar dados do Ibovespa (tentativa {tentativa + 1}/3): {e}"
                )
                if tentativa < 2:
                    time.sleep(1.0)
                else:
                    raise
        return False
    else:
        logger.error("Failed to collect data from all sources.")
        return False


if __name__ == "__main__":
    success = collect_and_save()
    if not success:
        sys.exit(1)
