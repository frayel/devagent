import json
import logging
import sys
from datetime import datetime, timezone, timedelta

import httpx

from app.database import HighlightsData, save_highlights_data
from app.collectors import mt5
from app.collectors.utils import fetch_with_retry, fechamento_anterior

logger = logging.getLogger(__name__)

OUTLIER_VARIACAO_DIA = 15.0

# List of highly liquid B3 tickers
TICKERS = [
    "PETR4",
    "VALE3",
    "ITUB4",
    "BBDC4",
    "B3SA3",
    "ABEV3",
    "BBDC3",
    "RENT3",
    "WEGE3",
    "BBAS3",
    "ITSA4",
    "SUZB3",
    "BPAC11",
    "RADL3",
    "EQTL3",
    "CSAN3",
    "PRIO3",
    "RDOR3",
    "RAIL3",
    "SBSP3",
    "VIVT3",
    "CMIG4",
    "LREN3",
    "CPLE3",
    "UGPA3",
    "ENEV3",
    "TIMS3",
    "TOTS3",
    "EGIE3",
    "HAPV3",
]


def consultar_segunda_fonte(
    symbol: str, price: float, fonte_primaria: str
) -> float | None:
    """Consulta a segunda fonte de mercado para confirmar variação extrema (Spec 135)."""
    try:
        current_date_str = (
            datetime.now(timezone.utc)
            .astimezone(timezone(timedelta(hours=-3)))
            .strftime("%Y-%m-%d")
        )
        if fonte_primaria == "mt5":
            # Segunda fonte é Yahoo Finance direto (sem interceptação MT5)
            url = f"https://query1.finance.yahoo.com/v8/finance/spark?symbols={symbol}.SA&range=15d&interval=1d"
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(
                    url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (compatible; B3Dashboard/1.0; +https://github.com/frayel/devagent)"
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    res = data.get("spark", {}).get("result", [])
                    if res and res[0].get("response"):
                        item = res[0]["response"][0]
                        meta2 = item.get("meta", {})
                        p2 = meta2.get("regularMarketPrice")
                        closes2 = (
                            item.get("indicators", {})
                            .get("quote", [{}])[0]
                            .get("close", [])
                        )
                        valid_c2 = [c for c in closes2 if c is not None]
                        timestamps2 = item.get("timestamp", [])
                        dates2 = [
                            datetime.fromtimestamp(t, tz=timezone.utc)
                            .astimezone(timezone(timedelta(hours=-3)))
                            .strftime("%Y-%m-%d")
                            for t in timestamps2
                            if t
                        ]
                        prev2 = fechamento_anterior(
                            valid_c2,
                            p2,
                            hoje=current_date_str,
                            meta=meta2,
                            datas=dates2,
                        )
                        if p2 and prev2 and prev2 > 0:
                            return ((p2 - prev2) / prev2) * 100
        else:
            # Fonte primária é Yahoo Finance. Segunda fonte é MT5 (se configurado)
            if mt5.configurado():
                bloco = mt5.bloco_yahoo(f"{symbol}.SA", "1d", "15d")
                if bloco and bloco.get("meta"):
                    meta2 = bloco["meta"]
                    p2 = meta2.get("regularMarketPrice")
                    closes2 = (
                        bloco.get("indicators", {})
                        .get("quote", [{}])[0]
                        .get("close", [])
                    )
                    valid_c2 = [c for c in closes2 if c is not None]
                    timestamps2 = bloco.get("timestamp", [])
                    dates2 = [
                        datetime.fromtimestamp(t, tz=timezone.utc)
                        .astimezone(timezone(timedelta(hours=-3)))
                        .strftime("%Y-%m-%d")
                        for t in timestamps2
                        if t
                    ]
                    prev2 = fechamento_anterior(
                        valid_c2,
                        p2,
                        hoje=current_date_str,
                        meta=meta2,
                        datas=dates2,
                    )
                    if p2 and prev2 and prev2 > 0:
                        return ((p2 - prev2) / prev2) * 100
    except Exception as e:
        logger.debug(f"Segunda fonte indisponível para {symbol}: {e}")
    return None


def fetch_yfinance() -> HighlightsData | None:
    parsed_results = []
    em_revisao_results = []
    ausentes_tickers = []
    up_count = 0
    down_count = 0
    pregao_data_str: str | None = None
    current_date_str = (
        datetime.now(timezone.utc)
        .astimezone(timezone(timedelta(hours=-3)))
        .strftime("%Y-%m-%d")
    )
    fonte_primaria = mt5.fonte_efetiva("yfinance")

    batch_size = 15
    batches = [TICKERS[i : i + batch_size] for i in range(0, len(TICKERS), batch_size)]

    with httpx.Client(timeout=10.0) as client:
        for batch in batches:
            symbols = ",".join([f"{t}.SA" for t in batch])
            url = f"https://query1.finance.yahoo.com/v8/finance/spark?symbols={symbols}&range=15d&interval=1d"
            try:
                response = fetch_with_retry(url, client=client)
                data = response.json()

                for item in data.get("spark", {}).get("result", []):
                    if not item.get("response"):
                        continue

                    symbol = item.get("symbol", "").replace(".SA", "")
                    meta = item["response"][0].get("meta", {})
                    price = meta.get("regularMarketPrice")

                    closes = (
                        item["response"][0]
                        .get("indicators", {})
                        .get("quote", [{}])[0]
                        .get("close", [])
                    )
                    valid_closes = [c for c in closes if c is not None]
                    timestamps = item["response"][0].get("timestamp", [])
                    dates = [
                        datetime.fromtimestamp(t, tz=timezone.utc)
                        .astimezone(timezone(timedelta(hours=-3)))
                        .strftime("%Y-%m-%d")
                        for t in timestamps
                        if t
                    ]

                    if timestamps and pregao_data_str is None:
                        dt_u = datetime.fromtimestamp(
                            timestamps[-1], tz=timezone.utc
                        ).astimezone(timezone(timedelta(hours=-3)))
                        pregao_data_str = dt_u.strftime("%d/%m/%Y")

                    prev_close = fechamento_anterior(
                        valid_closes,
                        price,
                        hoje=current_date_str,
                        meta=meta,
                        datas=dates,
                    )

                    if price is None or prev_close is None or prev_close <= 0:
                        ausentes_tickers.append(symbol)
                        continue

                    change_percent = ((price - prev_close) / prev_close) * 100
                    sparkline = valid_closes[-10:] if len(valid_closes) > 0 else []

                    asset_dict = {
                        "ticker": symbol,
                        "price": price,
                        "change_percent": change_percent,
                        "sparkline": sparkline,
                        "base": prev_close,
                        "fonte": fonte_primaria,
                        "janela": "15d",
                    }

                    if abs(change_percent) > OUTLIER_VARIACAO_DIA:
                        # Tenta confirmar com a segunda fonte
                        var_segunda = consultar_segunda_fonte(
                            symbol, price, fonte_primaria
                        )
                        if (
                            var_segunda is not None
                            and abs(change_percent - var_segunda) <= 0.5
                        ):
                            outra_fonte = (
                                "yfinance" if fonte_primaria == "mt5" else "mt5"
                            )
                            asset_dict["fonte"] = f"{fonte_primaria}+{outra_fonte}"
                            parsed_results.append(asset_dict)
                            if change_percent > 0:
                                up_count += 1
                            elif change_percent < 0:
                                down_count += 1
                        else:
                            em_revisao_results.append(asset_dict)
                    else:
                        parsed_results.append(asset_dict)
                        if change_percent > 0:
                            up_count += 1
                        elif change_percent < 0:
                            down_count += 1
            except httpx.HTTPError as e:
                logger.error(f"Error fetching batch {symbols} from yfinance: {e}")
                continue

    if not parsed_results and not em_revisao_results:
        return None

    parsed_results.sort(key=lambda x: x["change_percent"], reverse=True)
    highs = parsed_results[:5]
    lows = parsed_results[-5:]
    lows.sort(key=lambda x: x["change_percent"])

    total_count = len(parsed_results)

    return HighlightsData(
        timestamp=datetime.now(timezone.utc),
        highs_json=json.dumps(highs),
        lows_json=json.dumps(lows),
        fonte=fonte_primaria,
        up_count=up_count,
        down_count=down_count,
        total_count=total_count,
        em_revisao_json=json.dumps(em_revisao_results),
        pregao_data=pregao_data_str,
        ausentes_count=len(ausentes_tickers),
        ausentes_json=json.dumps(ausentes_tickers),
    )


def collect_and_save() -> bool:
    logger.info("Starting highlights collection...")
    data = None
    if mt5.configurado():
        # MetaTrader 5 é a fonte preferencial; sem ele, segue a ordem antiga.
        with mt5.exclusivo():
            data = fetch_yfinance()
    if not data:
        logger.info("Falling back highlights to yfinance...")
        data = fetch_yfinance()

    if data:
        save_highlights_data(data)
        logger.info("Saved highlights data.")
        return True
    else:
        logger.error("Failed to collect highlights data from all sources.")
        return False


if __name__ == "__main__":
    success = collect_and_save()
    if not success:
        sys.exit(1)
