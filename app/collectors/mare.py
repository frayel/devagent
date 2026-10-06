"""Coletor da Maré do mercado (spec 027).

Baixa duas séries diárias e entrega o cálculo a `app/services/mare.py`:

- a cesta `TICKERS` de `highlights.py` pelo `/v7/finance/spark`
  (`range=3mo&interval=1d`, fechamento e volume), em lotes de 15;
- o Ibovespa pelo `/v8/finance/chart` (`range=2y&interval=1d`), com a brapi
  (`range=2y`) como reserva.

As duas URLs do Yahoo passam por `fetch_with_retry`, que prefere o MetaTrader 5
quando ele está configurado (`app/collectors/mt5.py`). Se a cesta falhar
inteira, Fluxo e Volume ficam ausentes; se o Ibovespa falhar, a Calma fica
ausente. Com menos de dois componentes não há índice e nada é gravado.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import date, datetime, timezone

import httpx

from app.collectors import mt5
from app.collectors.highlights import TICKERS
from app.collectors.utils import fetch_with_retry
from app.database import MareData, save_mare_data
from app.services import mare

logger = logging.getLogger(__name__)

LOTE = 15
URL_CESTA = (
    "https://query1.finance.yahoo.com/v7/finance/spark"
    "?symbols={simbolos}&range=3mo&interval=1d"
)
URL_IBOV = (
    "https://query2.finance.yahoo.com/v8/finance/chart/%5EBVSP?range=2y&interval=1d"
)
URL_IBOV_BRAPI = (
    "https://brapi.dev/api/quote/%5EBVSP?token={token}&range=2y&interval=1d"
    "&fundamental=false"
)


def _dia(ts: int | float) -> date:
    return datetime.fromtimestamp(ts, tz=mare.BRT).date()


def _serie_do_bloco(bloco: dict) -> mare.SerieAcao:
    """Série dia -> (fechamento, volume) de um bloco do Yahoo (spark ou chart)."""
    try:
        tempos = bloco["timestamp"]
        cotacao = bloco["indicators"]["quote"][0]
        fechamentos = cotacao["close"]
        volumes = cotacao.get("volume") or [None] * len(tempos)
    except (KeyError, IndexError, TypeError):
        return {}
    serie: mare.SerieAcao = {}
    for t, c, v in zip(tempos, fechamentos, volumes):
        if t is None or c is None or v is None or c <= 0:
            continue
        serie[_dia(t)] = (float(c), float(v))
    return serie


def buscar_cesta(client: httpx.Client) -> dict[str, mare.SerieAcao]:
    series: dict[str, mare.SerieAcao] = {}
    for i in range(0, len(TICKERS), LOTE):
        lote = TICKERS[i : i + LOTE]
        url = URL_CESTA.format(simbolos=",".join(f"{t}.SA" for t in lote))
        try:
            dados = fetch_with_retry(url, client=client).json()
        except (httpx.HTTPError, ValueError) as e:
            logger.error("Maré: lote %s falhou: %s", ",".join(lote), e)
            continue
        for item in dados.get("spark", {}).get("result", []) or []:
            resposta = item.get("response") or []
            if not resposta:
                continue
            serie = _serie_do_bloco(resposta[0])
            if serie:
                series[item.get("symbol", "").replace(".SA", "")] = serie
    return series


def _ibov_yahoo(client: httpx.Client) -> dict[date, float]:
    dados = fetch_with_retry(URL_IBOV, client=client).json()
    bloco = dados["chart"]["result"][0]
    tempos = bloco["timestamp"]
    fechamentos = bloco["indicators"]["quote"][0]["close"]
    return {_dia(t): float(c) for t, c in zip(tempos, fechamentos) if c}


def _ibov_brapi(client: httpx.Client) -> dict[date, float]:
    token = os.environ.get("BRAPI_TOKEN")
    if not token:
        return {}
    dados = fetch_with_retry(URL_IBOV_BRAPI.format(token=token), client=client).json()
    historico = dados["results"][0].get("historicalDataPrice", [])
    return {
        _dia(h["date"]): float(h["close"])
        for h in historico
        if h.get("date") and h.get("close")
    }


def buscar_ibov(client: httpx.Client) -> tuple[dict[date, float], bool]:
    """Fechamentos diários do Ibovespa e se veio da brapi."""
    try:
        serie = _ibov_yahoo(client)
        if serie:
            return serie, False
    except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as e:
        logger.error("Maré: Ibovespa no Yahoo falhou: %s", e)
    try:
        return _ibov_brapi(client), True
    except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as e:
        logger.error("Maré: Ibovespa na brapi falhou: %s", e)
        return {}, False


def coletar(agora: datetime | None = None) -> MareData | None:
    agora = agora or datetime.now(timezone.utc)
    with httpx.Client(timeout=10.0) as client:
        cesta = buscar_cesta(client)
        ibov, usou_brapi = buscar_ibov(client)

    atual, historico = mare.calcular(cesta, ibov, agora)
    if atual is None or atual.valor is None:
        logger.error(
            "Maré: menos de dois componentes (%d ações, %d pregões do Ibovespa)",
            len(cesta),
            len(ibov),
        )
        return None

    fonte = mt5.fonte_efetiva("yfinance")
    if usou_brapi and ibov:
        fonte += "+brapi"
    c = atual.componentes
    return MareData(
        timestamp=agora,
        valor=atual.valor,
        fluxo=c["fluxo"],
        calma=c["calma"],
        volume=c["volume"],
        historico_json=json.dumps(
            [{"data": h.dia.isoformat(), "valor": h.valor} for h in historico]
        ),
        fonte=fonte,
    )


def collect_and_save() -> bool:
    dado = coletar()
    if dado is None:
        return False
    save_mare_data(dado)
    logger.info("Maré gravada: %s (%s)", dado.valor, mare.faixa(dado.valor))
    return True


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    collect_and_save()
