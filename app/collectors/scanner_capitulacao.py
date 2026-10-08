import json
import logging
from datetime import datetime, timezone
import httpx
import asyncio
from app.collectors.highlights import TICKERS
from app.collectors import mt5
from app.database import ScannerCapitulacaoData, save_scanner_capitulacao_data

logger = logging.getLogger(__name__)


async def fetch_ticker(client, ticker):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}.SA?interval=15m&range=2d"
    try:
        resp = await client.get(url, timeout=10.0)
        resp.raise_for_status()
        return ticker, resp.json()
    except Exception:
        return ticker, None


async def fetch_all():
    async with httpx.AsyncClient() as client:
        tasks = [fetch_ticker(client, t) for t in TICKERS]
        return await asyncio.gather(*tasks)


def collect_and_save() -> bool:
    alertas = []

    try:
        results = asyncio.run(fetch_all())
    except Exception:
        return False

    for ticker, data in results:
        if not data:
            continue

        try:
            result = data.get("chart", {}).get("result", [])[0]
            indicators = result.get("indicators", {}).get("quote", [{}])[0]

            closes = indicators.get("close", [])
            opens = indicators.get("open", [])
            highs = indicators.get("high", [])
            lows = indicators.get("low", [])
            volumes = indicators.get("volume", [])
            timestamps = result.get("timestamp", [])

            if (
                not all([closes, opens, highs, lows, volumes, timestamps])
                or len(closes) < 8
            ):
                continue

            valid = []
            for t, o, h, lo, c, v in zip(
                timestamps, opens, highs, lows, closes, volumes
            ):
                if None not in (t, o, h, lo, c, v):
                    valid.append((t, o, h, lo, c, v))

            if len(valid) < 8:
                continue

            dt_valid = [datetime.fromtimestamp(v[0], tz=timezone.utc) for v in valid]
            today = dt_valid[-1].date()

            today_bars = [v for i, v in enumerate(valid) if dt_valid[i].date() == today]
            yesterday_bars = [
                v for i, v in enumerate(valid) if dt_valid[i].date() < today
            ]

            if not today_bars or not yesterday_bars:
                continue

            yesterday_close = yesterday_bars[-1][4]
            current_price = today_bars[-1][4]

            if yesterday_close <= 0:
                continue

            queda_pct = ((current_price - yesterday_close) / yesterday_close) * 100

            if queda_pct <= -2.0:
                today_vols = [b[5] for b in today_bars]
                avg_vol = sum(today_vols) / len(today_vols) if today_vols else 0
                if avg_vol == 0:
                    continue

                recent_bars = today_bars[-8:]
                for b in recent_bars:
                    h = b[2]
                    lo = b[3]
                    c = b[4]
                    v = b[5]
                    t = b[0]
                    if h - lo > 0:
                        sombra_inf = c - lo
                        corpo_total = h - lo
                        if v >= 3 * avg_vol and sombra_inf > 0.5 * corpo_total:
                            from datetime import timedelta

                            delta_brt = timedelta(hours=-3)
                            dt_brt = datetime.fromtimestamp(
                                t, tz=timezone.utc
                            ).astimezone(timezone(delta_brt))
                            alertas.append(
                                {
                                    "ticker": ticker,
                                    "queda_pct": queda_pct,
                                    "texto": f"{dt_brt.strftime('%H:%M')} - Vol {v / avg_vol:.1f}x",
                                }
                            )
                            break
        except Exception:
            continue

    alertas = alertas[:3]
    save_scanner_capitulacao_data(
        ScannerCapitulacaoData(
            timestamp=datetime.now(timezone.utc),
            alertas_json=json.dumps(alertas),
            fonte=mt5.fonte_efetiva("yfinance"),
        )
    )
    return True
