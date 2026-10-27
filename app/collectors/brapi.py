import logging
import os
from datetime import datetime, timezone, timedelta

import httpx

from app.collectors import registro_fontes
from app.collectors.utils import fetch_with_retry

logger = logging.getLogger(__name__)

BRT = timezone(timedelta(hours=-3))

_disjuntor_ate: datetime | None = None
_esgotado_mensal: bool = False


def disjuntor_armado() -> bool:
    global _disjuntor_ate
    global _esgotado_mensal

    if _esgotado_mensal:
        hoje = datetime.now(BRT)
        if _disjuntor_ate and hoje >= _disjuntor_ate:
            _esgotado_mensal = False
            _disjuntor_ate = None
            return False
        return True

    if _disjuntor_ate:
        if datetime.now(BRT) < _disjuntor_ate:
            return True
        _disjuntor_ate = None
    return False


def desligar_brapi_ate_meia_noite():
    global _disjuntor_ate
    agora = datetime.now(BRT)
    amanha = agora + timedelta(days=1)
    meia_noite = datetime(amanha.year, amanha.month, amanha.day, 0, 0, 0, tzinfo=BRT)
    _disjuntor_ate = meia_noite


def desligar_brapi_ate_proximo_mes():
    global _esgotado_mensal, _disjuntor_ate
    agora = datetime.now(BRT)
    ano = agora.year
    mes = agora.month + 1
    if mes > 12:
        mes = 1
        ano += 1
    primeiro_dia_mes = datetime(ano, mes, 1, 0, 0, 0, tzinfo=BRT)
    _disjuntor_ate = primeiro_dia_mes
    _esgotado_mensal = True


def fazer_chamada(url: str, headers: dict) -> httpx.Response | None:
    if disjuntor_armado():
        logger.warning("brapi está desligada pelo disjuntor")
        return None

    try:
        response = fetch_with_retry(url, headers=headers, timeout=10.0)
        return response
    except httpx.HTTPStatusError as e:
        status = e.response.status_code
        if status == 403:
            logger.error("brapi.dev retornou 403. Desligando até meia noite.")
            desligar_brapi_ate_meia_noite()
            registro_fontes.falha("brapi", "HTTP 403", grave=True, url=url, status=403)
        elif status == 429:
            logger.error("brapi.dev retornou 429.")
            if "quota" in e.response.text.lower() or "limit" in e.response.text.lower():
                desligar_brapi_ate_proximo_mes()
            else:
                desligar_brapi_ate_meia_noite()
            registro_fontes.falha("brapi", "HTTP 429", grave=True, url=url, status=429)
        raise e


def cotacao(ticker: str, **params) -> dict | None:
    if "," in ticker or "%2C" in ticker:
        raise ValueError("ticker não pode conter vírgula ou %2C")

    token = os.environ.get("BRAPI_TOKEN")
    if not token:
        logger.warning("BRAPI_TOKEN not set")
        return None

    query = "&".join(f"{k}={v}" for k, v in params.items())
    url = (
        f"https://brapi.dev/api/quote/{ticker}?{query}"
        if query
        else f"https://brapi.dev/api/quote/{ticker}"
    )

    headers = {"Authorization": f"Bearer {token}"}

    try:
        response = fazer_chamada(url, headers=headers)
        if response:
            data = response.json()
            if "results" in data and data["results"]:
                return data["results"][0]
    except Exception as e:
        logger.error(f"Erro ao buscar cotacao brapi para {ticker}: {e}")
    return None


def cotacoes(tickers: list[str], **params) -> dict[str, dict]:
    resultados = {}
    for ticker in tickers:
        try:
            item = cotacao(ticker, **params)
            if item:
                resultados[ticker] = item
        except ValueError:
            pass
    return resultados


def quote_list(**params) -> list | None:
    token = os.environ.get("BRAPI_TOKEN")
    if not token:
        return None
    query = "&".join(f"{k}={v}" for k, v in params.items())
    url = (
        f"https://brapi.dev/api/quote/list?{query}"
        if query
        else "https://brapi.dev/api/quote/list"
    )
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = fazer_chamada(url, headers=headers)
        if response:
            return response.json().get("stocks", [])
    except Exception:
        pass
    return None
