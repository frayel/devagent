"""Consenso de analistas do Yahoo Finance (spec 159).

Uma rodada por dia, na janela de fechamento: cookie em `fc.yahoo.com`, crumb
em `getcrumb` e um `quoteSummary` (`financialData`) por ativo da carteira.

Não usa `fetch_with_retry`: o `registro_fontes` atribui todo domínio do Yahoo à
integração "Yahoo Finance", e um 401 aqui marcaria como fora do ar o `chart`,
que é outra coisa e funciona. Bloqueio (401, 429 ou 3 ativos seguidos sem
resposta) pausa a fonte por 24 h, com a pausa gravada no banco.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx

from app import calendario
from app.consultor import armazenamento
from app.consultor.universo import CARTEIRA_IBOVESPA

logger = logging.getLogger(__name__)

URL_COOKIE = "https://fc.yahoo.com"
URL_CRUMB = "https://query2.finance.yahoo.com/v1/test/getcrumb"
URL_RESUMO = "https://query2.finance.yahoo.com/v10/finance/quoteSummary/{ticker}.SA"
TIMEOUT = 10.0
PAUSA = timedelta(hours=24)
FALHAS_SEGUIDAS = 3
CABECALHOS = {"User-Agent": "Mozilla/5.0 (compatible; painel-ibovespa)"}
BRT = timezone(timedelta(hours=-3))


class _Bloqueio(Exception):
    """A fonte recusou ou não respondeu: a rodada para e a fonte pausa."""


def _dt(texto: str | None) -> datetime | None:
    if not texto:
        return None
    try:
        d = datetime.fromisoformat(str(texto))
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def em_pausa(status: dict | None, agora: datetime) -> bool:
    if not status or status.get("status") != "pausa":
        return False
    ultima = _dt(status.get("ultima_tentativa")) or _dt(status.get("desde"))
    return ultima is not None and agora - ultima < PAUSA


def _ja_tentou_hoje(status: dict | None, agora: datetime) -> bool:
    """No máximo uma rodada por dia (BRT), qualquer que tenha sido o resultado."""
    ultima = _dt((status or {}).get("ultima_tentativa"))
    return (
        ultima is not None
        and ultima.astimezone(BRT).date() == agora.astimezone(BRT).date()
    )


def _bruto(campo) -> float | None:
    if isinstance(campo, dict):
        campo = campo.get("raw")
    if isinstance(campo, bool) or not isinstance(campo, (int, float)):
        return None
    return float(campo)


def ler_financial_data(ticker: str, corpo: dict) -> dict | None:
    """Linha a gravar, ou None se o ativo não tem cobertura de analistas."""
    try:
        fd = corpo["quoteSummary"]["result"][0]["financialData"]
    except (KeyError, IndexError, TypeError):
        return None
    if not isinstance(fd, dict):
        return None
    media = _bruto(fd.get("recommendationMean"))
    analistas = _bruto(fd.get("numberOfAnalystOpinions"))
    if media is None or analistas is None or analistas <= 0:
        return None
    if not 1 <= media <= 5:
        return None
    return {
        "ticker": ticker,
        "recomendacao_media": media,
        "analistas": int(analistas),
        "alvo_medio": _bruto(fd.get("targetMeanPrice")),
        "alvo_minimo": _bruto(fd.get("targetLowPrice")),
        "alvo_maximo": _bruto(fd.get("targetHighPrice")),
    }


def _recusou(resp: httpx.Response) -> bool:
    return resp.status_code in (401, 429)


def _rodada(client: httpx.Client) -> list[dict]:
    try:
        client.get(URL_COOKIE)  # só o cookie importa; o status costuma ser 404
        resp = client.get(URL_CRUMB)
    except httpx.HTTPError as e:
        raise _Bloqueio(f"sem resposta ao pedir o crumb ({type(e).__name__})")
    crumb = resp.text.strip()
    if resp.status_code != 200 or not crumb or "<" in crumb:
        raise _Bloqueio(f"HTTP {resp.status_code}")

    linhas: list[dict] = []
    seguidas = 0
    for ticker in CARTEIRA_IBOVESPA:
        try:
            r = client.get(
                URL_RESUMO.format(ticker=ticker),
                params={"modules": "financialData", "crumb": crumb},
            )
        except httpx.HTTPError:
            r = None
        if r is not None and _recusou(r):
            raise _Bloqueio(f"HTTP {r.status_code}", linhas)
        if r is None or r.status_code >= 500:
            seguidas += 1
            if seguidas >= FALHAS_SEGUIDAS:
                raise _Bloqueio(
                    f"{FALHAS_SEGUIDAS} ativos seguidos sem resposta", linhas
                )
            continue
        seguidas = 0
        if r.status_code != 200:
            continue  # ativo desconhecido do Yahoo: segue para o próximo
        try:
            linha = ler_financial_data(ticker, r.json())
        except ValueError:
            linha = None
        if linha:
            linhas.append(linha)
    return linhas


def collect_and_save(
    agora: datetime | None = None, client: httpx.Client | None = None
) -> bool:
    agora = agora or datetime.now(timezone.utc)
    data = calendario.ultimo_pregao_fechado(agora).isoformat()
    if armazenamento.tem_consenso_yahoo(data):
        return True
    status = armazenamento.get_consenso_yahoo_status()
    if em_pausa(status, agora) or _ja_tentou_hoje(status, agora):
        return True

    proprio = client is None
    client = client or httpx.Client(
        timeout=TIMEOUT, follow_redirects=True, headers=CABECALHOS
    )
    try:
        linhas = _rodada(client)
    except _Bloqueio as b:
        motivo = b.args[0]
        parciais = b.args[1] if len(b.args) > 1 else []
        armazenamento.save_consenso_yahoo(parciais, data, agora.isoformat())
        # Bloqueio que continua mantém o início, para a regra dos 7 dias.
        desde = (
            status["desde"]
            if status and status.get("status") == "pausa"
            else agora.isoformat()
        )
        armazenamento.set_consenso_yahoo_status("pausa", motivo, agora, desde)
        logger.warning("Yahoo · consenso em pausa por 24 h: %s", motivo)
        return True
    finally:
        if proprio:
            client.close()

    armazenamento.save_consenso_yahoo(linhas, data, agora.isoformat())
    armazenamento.set_consenso_yahoo_status("ok", "", agora)
    logger.info(
        "Yahoo · consenso: %d de %d ativos em %s",
        len(linhas),
        len(CARTEIRA_IBOVESPA),
        data,
    )
    return True
