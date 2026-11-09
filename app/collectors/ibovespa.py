import json
import logging
import sys
import time
from datetime import datetime, timezone, timedelta

import httpx

from app.database import IbovespaData, save_ibovespa_data
from app.collectors import mt5
from app.collectors.utils import fetch_with_retry, fechamento_anterior

logger = logging.getLogger(__name__)

# Variação diária acima disto é tratada como dado errado da fonte e descartada.
# Era 12%: caso relatado em 29/10/2026 de que o Ibovespa teria variado 15,99% (relatado, não confirmado por fonte independente).
# Variações > 10% exigem confirmação por segunda fonte (Spec 136).
VARIACAO_DIARIA_MAXIMA = 20.0  # %
LIMIAR_CONFIRMACAO_EXTREMA = 10.0  # % (Spec 136)
DIVERGENCIA_MAXIMA_CONFIRMACAO = 0.5  # p.p. (Spec 136)

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

        previous_close = fechamento_anterior(
            valid_closes,
            current_price,
            hoje=current_date_str,
            meta=meta,
            datas=valid_dates,
        )
        if previous_close is None:
            logger.warning(
                "previous_close ausente em meta e série; usando current_price como fallback."
            )
            previous_close = float(current_price)

        previous_close = float(previous_close)

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


def obter_variacao_segunda_fonte(fonte_primaria: str) -> float | None:
    """Consulta a segunda fonte de mercado para confirmar variação extrema do Ibovespa (Spec 136)."""
    try:
        if fonte_primaria == "mt5":
            with mt5.ignorado():
                dado_yahoo = fetch_yfinance()
                if (
                    dado_yahoo
                    and dado_yahoo.previous_close
                    and dado_yahoo.previous_close > 0
                ):
                    return (
                        (dado_yahoo.current_price - dado_yahoo.previous_close)
                        / dado_yahoo.previous_close
                    ) * 100
        else:
            if mt5.configurado():
                with mt5.exclusivo():
                    dado_mt5 = fetch_yfinance()
                    if (
                        dado_mt5
                        and dado_mt5.previous_close
                        and dado_mt5.previous_close > 0
                    ):
                        return (
                            (dado_mt5.current_price - dado_mt5.previous_close)
                            / dado_mt5.previous_close
                        ) * 100
    except Exception as e:
        logger.debug(f"Segunda fonte indisponível: {e}")
    return None


def collect_and_save() -> bool:
    logger.info("Starting collection...")
    data = None
    fonte_primaria = None
    if mt5.configurado():
        try:
            with mt5.exclusivo():
                data = fetch_yfinance()
            if data:
                fonte_primaria = "mt5"
        except Exception as e:
            logger.info(f"MT5 indisponível ({e}); tentando Yahoo...")

    if not data:
        logger.info("Falling back to yfinance...")
        data = fetch_yfinance()
        if data:
            fonte_primaria = "yfinance"

    if not data or not fonte_primaria:
        logger.error("Failed to collect data from all sources.")
        return False

    if data.previous_close and data.previous_close > 0:
        var_pct = (
            (data.current_price - data.previous_close) / data.previous_close
        ) * 100

        if abs(var_pct) > VARIACAO_DIARIA_MAXIMA:
            logger.error(
                f"Variação implausível descartada: {var_pct:+.2f}% (teto {VARIACAO_DIARIA_MAXIMA}%)"
            )
            return False

        if abs(var_pct) > LIMIAR_CONFIRMACAO_EXTREMA:
            outra_fonte = "yfinance" if fonte_primaria == "mt5" else "mt5"
            var_segunda = obter_variacao_segunda_fonte(fonte_primaria)

            if var_segunda is None:
                logger.error(
                    f"Variação acima de 10% ({var_pct:+.2f}%) sem segunda fonte: "
                    f"a outra fonte ({outra_fonte}) não respondeu ou não está configurada."
                )
                return False

            diff = abs(var_pct - var_segunda)
            if diff > DIVERGENCIA_MAXIMA_CONFIRMACAO:
                logger.error(
                    f"Variação acima de 10% divergente: {var_pct:+.2f}% ({fonte_primaria}) "
                    f"e {var_segunda:+.2f}% ({outra_fonte}) (diferença de {diff:.2f} p.p. > {DIVERGENCIA_MAXIMA_CONFIRMACAO} p.p.)"
                )
                return False

            logger.info(
                f"variação acima de 10% confirmada por {fonte_primaria} e {outra_fonte} "
                f"({var_pct:+.2f}% vs {var_segunda:+.2f}%)"
            )

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


if __name__ == "__main__":
    success = collect_and_save()
    if not success:
        sys.exit(1)
