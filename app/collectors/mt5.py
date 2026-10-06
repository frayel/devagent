"""MetaTrader 5 como fonte preferencial de cotações.

O terminal MT5 roda numa máquina Windows com o servidor `mt5api`
(https://github.com/dceoy/mt5api), que expõe os dados por HTTP com
autenticação pelo header `X-API-Key`. Este módulo conversa com ele.

Como entra na coleta: os coletores continuam montando as URLs do Yahoo
Finance (`/v7/finance/spark` e `/v8/finance/chart`). `fetch_with_retry`
pergunta a este módulo se ele consegue responder a URL; se consegue, devolve
uma resposta no mesmo formato do Yahoo, montada com as barras do MT5, e o
Yahoo nem é chamado. Se o MT5 falhar, a requisição segue para o Yahoo como
antes. Assim todos os painéis preferem o MT5 sem que cada coletor precise
de um parser novo.

Transparência (PRODUTO.md, seção 1): cada requisição registra a fonte que de
fato respondeu, e `fonte_efetiva` devolve o rótulo honesto para o painel:
`mt5`, `mt5+yfinance` (parte de cada) ou o rótulo original.

Configuração (variáveis de ambiente):

- `MT5_API_URL`: base da API, por exemplo `http://host:8000/api/v1`.
  Sem ela, o módulo fica desligado e nada muda.
- `MT5_API_KEY`: a chave configurada no servidor (`MT5API_SECRET_KEY`).
- `MT5_SIMBOLOS`: JSON opcional que traduz símbolos do Yahoo para os da
  corretora. Padrão: `{"^BVSP": "IBOV", "BRL=X": "DOL$"}`. Ações `XXXX4.SA`
  viram `XXXX4`. Símbolos sem tradução continuam vindo do Yahoo.
- `MT5_FUSO_SERVIDOR`: deslocamento do relógio do servidor da corretora em
  relação a UTC, em horas. Padrão `-3` (Brasília). Só afeta barras
  intradiárias.
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from typing import Any, Iterator
from urllib.parse import parse_qs, unquote, urlparse

import httpx

logger = logging.getLogger(__name__)

FONTE = "mt5"
FONTE_YAHOO = "yfinance"

BARRAS_DIARIAS = 300  # cobre range=1y com folga
BARRAS_INTRADIA = 80  # um pregão inteiro em M15 tem ~32 barras
TTL_DIARIO = 300.0
TTL_INTRADIA = 120.0
PAUSA_APOS_FALHA = 300.0  # servidor fora do ar: não insiste por 5 minutos
PAUSA_SIMBOLO = 300.0  # símbolo que o terminal não serviu: não insiste por 5 minutos
TIMEOUT = 10.0

INTERVALOS = {
    "1m": "M1",
    "2m": "M2",
    "5m": "M5",
    "15m": "M15",
    "30m": "M30",
    "60m": "H1",
    "1h": "H1",
    "1d": "D1",
}
SEGUNDOS_TIMEFRAME = {
    "M1": 60,
    "M2": 120,
    "M5": 300,
    "M15": 900,
    "M30": 1800,
    "H1": 3600,
    "D1": 86400,
}

_cache: dict[tuple[str, str], tuple[float, list[dict[str, Any]]]] = {}
_indisponivel_ate = 0.0
_motivo_pausa = ""
_simbolos_falhos: dict[tuple[str, str], tuple[float, str]] = {}
_trava = threading.Lock()
_local = threading.local()


class Mt5Indisponivel(Exception):
    """O MT5 não respondeu ou não conhece o símbolo."""


# --------------------------------------------------------------------------
# Configuração
# --------------------------------------------------------------------------


def url_base() -> str | None:
    url = os.environ.get("MT5_API_URL", "").strip().rstrip("/")
    return url or None


def configurado() -> bool:
    return url_base() is not None


def _mapa_simbolos() -> dict[str, str]:
    # DOL$: dólar futuro cheio contínuo. A correlação usa só retornos diários,
    # então a escala (pontos por US$ 1.000) não importa.
    mapa = {"^BVSP": "IBOV", "BRL=X": "DOL$"}
    bruto = os.environ.get("MT5_SIMBOLOS", "").strip()
    if bruto:
        try:
            extra = json.loads(bruto)
            if isinstance(extra, dict):
                mapa.update({str(k): str(v) for k, v in extra.items()})
        except json.JSONDecodeError:
            logger.error("MT5_SIMBOLOS não é um JSON válido; usando o padrão")
    return mapa


def simbolo_mt5(simbolo_yahoo: str) -> str | None:
    """Traduz `PETR4.SA` para `PETR4`. Devolve None se não houver tradução."""
    mapa = _mapa_simbolos()
    if simbolo_yahoo in mapa:
        return mapa[simbolo_yahoo] or None
    if simbolo_yahoo.endswith(".SA"):
        return simbolo_yahoo[: -len(".SA")]
    return None


def _fuso_servidor() -> timezone:
    try:
        horas = float(os.environ.get("MT5_FUSO_SERVIDOR", "-3"))
    except ValueError:
        horas = -3.0
    return timezone(timedelta(hours=horas))


# --------------------------------------------------------------------------
# Rastreio da fonte usada (transparência)
# --------------------------------------------------------------------------


def _fontes() -> set[str]:
    if not hasattr(_local, "fontes"):
        _local.fontes = set()
    fontes: set[str] = _local.fontes
    return fontes


def registrar_fonte(fonte: str) -> None:
    _fontes().add(fonte)


def reiniciar_rastreio() -> None:
    _fontes().clear()


def fonte_efetiva(padrao: str) -> str:
    """Rótulo de fonte para o painel, conforme quem respondeu de fato.

    O agendador zera o registro antes de cada coletor (`reiniciar_rastreio`).
    """
    fontes = _fontes()
    usou_mt5 = FONTE in fontes
    usou_yahoo = FONTE_YAHOO in fontes
    if usou_mt5 and usou_yahoo:
        return f"{FONTE}+{FONTE_YAHOO}"
    if usou_mt5:
        return FONTE
    return padrao


@contextmanager
def exclusivo() -> Iterator[None]:
    """Dentro do bloco, URLs do Yahoo são servidas só pelo MT5, sem recurso.

    Serve para coletores cuja fonte principal não é o Yahoo (brapi): eles
    tentam o MT5 primeiro e, se falhar, seguem a ordem original.
    """
    anterior = getattr(_local, "exclusivo", False)
    _local.exclusivo = True
    try:
        yield
    finally:
        _local.exclusivo = anterior


def em_modo_exclusivo() -> bool:
    return bool(getattr(_local, "exclusivo", False))


# --------------------------------------------------------------------------
# Cliente da mt5api
# --------------------------------------------------------------------------


def _hora_da_barra(valor: Any) -> datetime:
    """Horário da barra no relógio do servidor (sem fuso)."""
    if isinstance(valor, (int, float)):
        return datetime.fromtimestamp(valor, tz=timezone.utc).replace(tzinfo=None)
    texto = str(valor).replace("Z", "+00:00")
    return datetime.fromisoformat(texto).replace(tzinfo=None)


def _pausar_servidor(motivo: str) -> None:
    """Falha do servidor inteiro (rede, chave): vale para todos os símbolos."""
    global _indisponivel_ate, _motivo_pausa
    _indisponivel_ate = time.time() + PAUSA_APOS_FALHA
    _motivo_pausa = motivo


def _detalhe_erro(resposta: httpx.Response) -> str:
    """Texto do erro no formato RFC 7807 da mt5api, ou o começo do corpo."""
    try:
        corpo = resposta.json()
    except ValueError:
        return resposta.text[:150]
    if isinstance(corpo, dict):
        detalhe = corpo.get("detail")
        if isinstance(detalhe, dict):
            detalhe = detalhe.get("detail")
        if detalhe:
            return str(detalhe)[:150]
    return str(corpo)[:150]


def _baixar_barras(simbolo: str, timeframe: str, quantidade: int) -> list[dict]:
    base = url_base()
    if base is None:
        raise Mt5Indisponivel("MT5_API_URL não configurada")
    agora = time.time()
    if agora < _indisponivel_ate:
        raise Mt5Indisponivel(f"servidor MT5 em pausa: {_motivo_pausa}")
    falha = _simbolos_falhos.get((simbolo, timeframe))
    if falha and agora < falha[0]:
        raise Mt5Indisponivel(falha[1])

    from app.collectors.utils import _enforce_rate_limit, _get_domain

    url = f"{base}/rates/from-pos"
    params: dict[str, str | int] = {
        "symbol": simbolo,
        "timeframe": timeframe,
        "start_pos": 0,
        "count": quantidade,
    }
    headers = {"Accept": "application/json"}
    chave = os.environ.get("MT5_API_KEY", "").strip()
    if chave:
        headers["X-API-Key"] = chave

    _enforce_rate_limit(_get_domain(url))
    try:
        resposta = httpx.get(url, params=params, headers=headers, timeout=TIMEOUT)
    except httpx.RequestError as e:
        motivo = f"{type(e).__name__} ao conectar em {base}"
        _pausar_servidor(motivo)
        logger.warning("MT5 fora do ar (%s); usando outras fontes", motivo)
        raise Mt5Indisponivel(motivo) from e

    if resposta.status_code in (401, 403):
        motivo = f"chave recusada (HTTP {resposta.status_code})"
        _pausar_servidor(motivo)
        logger.error("MT5 recusou a chave: confira MT5_API_KEY")
        raise Mt5Indisponivel(motivo)
    if resposta.status_code != 200:
        # A mt5api devolve 503 quando o terminal não serve aquele símbolo
        # (inexistente, fora da Observação do Mercado, sem histórico). É uma
        # falha do símbolo, não do servidor: só ele fica em pausa.
        motivo = f"HTTP {resposta.status_code}: {_detalhe_erro(resposta)}"
        with _trava:
            _simbolos_falhos[(simbolo, timeframe)] = (agora + PAUSA_SIMBOLO, motivo)
        logger.warning("MT5 não serviu %s %s (%s)", simbolo, timeframe, motivo)
        raise Mt5Indisponivel(motivo)

    try:
        dados = resposta.json().get("data")
    except (ValueError, AttributeError) as e:
        raise Mt5Indisponivel("resposta não é JSON") from e
    if not isinstance(dados, list) or not dados:
        raise Mt5Indisponivel(f"sem barras para {simbolo}")

    lidas: list[dict[str, Any]] = []
    for b in dados:
        try:
            volume = b.get("real_volume") or b.get("tick_volume") or 0
            lidas.append(
                {
                    "hora": _hora_da_barra(b["time"]),
                    "open": float(b["open"]),
                    "high": float(b["high"]),
                    "low": float(b["low"]),
                    "close": float(b["close"]),
                    "volume": int(volume),
                }
            )
        except (KeyError, TypeError, ValueError):
            continue
    if not lidas:
        raise Mt5Indisponivel(f"barras ilegíveis para {simbolo}")
    lidas.sort(key=lambda x: x["hora"])
    return lidas


def barras(simbolo: str, timeframe: str) -> list[dict]:
    """Barras do símbolo, com cache curto para servir vários painéis."""
    chave = (simbolo, timeframe)
    agora = time.time()
    with _trava:
        guardado = _cache.get(chave)
    if guardado and guardado[0] > agora:
        return guardado[1]
    diario = timeframe == "D1"
    resultado = _baixar_barras(
        simbolo, timeframe, BARRAS_DIARIAS if diario else BARRAS_INTRADIA
    )
    with _trava:
        _cache[chave] = (agora + (TTL_DIARIO if diario else TTL_INTRADIA), resultado)
    return resultado


def limpar_cache() -> None:
    global _indisponivel_ate, _motivo_pausa
    with _trava:
        _cache.clear()
        _simbolos_falhos.clear()
    _indisponivel_ate = 0.0
    _motivo_pausa = ""


# --------------------------------------------------------------------------
# Tradução para o formato do Yahoo Finance
# --------------------------------------------------------------------------


def _recortar_diario(lista: list[dict], intervalo: str) -> list[dict]:
    m = re.fullmatch(r"(\d+)(d|wk|mo|y)", intervalo)
    if intervalo in ("max", "ytd") or not m:
        if intervalo == "ytd":
            ano = lista[-1]["hora"].year
            return [b for b in lista if b["hora"].year == ano]
        return lista
    n, unidade = int(m.group(1)), m.group(2)
    if unidade == "d":
        return lista[-n:]
    dias = {"wk": 7, "mo": 30.4375, "y": 365.25}[unidade] * n
    limite: date = lista[-1]["hora"].date() - timedelta(days=round(dias))
    return [b for b in lista if b["hora"].date() > limite]


def _epoch_diario(hora: datetime) -> int:
    # Mesma convenção do Yahoo para a B3: o candle diário marca 13:00 UTC
    # (10:00 BRT). A data é a do pregão em qualquer fuso brasileiro.
    meio = datetime(hora.year, hora.month, hora.day, 13, tzinfo=timezone.utc)
    return int(meio.timestamp())


def _epoch_intradia(hora: datetime) -> int:
    return int(hora.replace(tzinfo=_fuso_servidor()).timestamp())


def bloco_yahoo(simbolo_yahoo: str, intervalo: str, janela: str) -> dict:
    """Um item `response[0]` (spark) ou `result[0]` (chart) do Yahoo."""
    simbolo = simbolo_mt5(simbolo_yahoo)
    if simbolo is None:
        raise Mt5Indisponivel(f"sem tradução para {simbolo_yahoo}")
    timeframe = INTERVALOS.get(intervalo)
    if timeframe is None:
        raise Mt5Indisponivel(f"intervalo {intervalo} não suportado")

    diarias = barras(simbolo, "D1")
    if timeframe == "D1":
        janela_barras = _recortar_diario(diarias, janela)
        epochs = [_epoch_diario(b["hora"]) for b in janela_barras]
        primeira = janela_barras[0]["hora"] if janela_barras else None
        anteriores = [b for b in diarias if primeira and b["hora"] < primeira]
    else:
        intradia = barras(simbolo, timeframe)
        dias_pedidos = _recortar_diario(diarias, janela)
        datas = {b["hora"].date() for b in dias_pedidos} or {
            intradia[-1]["hora"].date()
        }
        janela_barras = [b for b in intradia if b["hora"].date() in datas]
        epochs = [_epoch_intradia(b["hora"]) for b in janela_barras]
        primeira_data = min(datas)
        anteriores = [b for b in diarias if b["hora"].date() < primeira_data]

    if not janela_barras:
        raise Mt5Indisponivel(f"janela vazia para {simbolo_yahoo}")

    ultima_diaria = diarias[-1]
    fech_anterior_janela = anteriores[-1]["close"] if anteriores else None
    fech_anterior_dia = diarias[-2]["close"] if len(diarias) > 1 else None
    meta = {
        "symbol": simbolo_yahoo,
        "currency": "BRL",
        "exchangeName": "MT5",
        "dataGranularity": intervalo,
        "range": janela,
        "regularMarketPrice": ultima_diaria["close"],
        "regularMarketTime": epochs[-1],
        "regularMarketDayHigh": ultima_diaria["high"],
        "regularMarketDayLow": ultima_diaria["low"],
        "regularMarketVolume": ultima_diaria["volume"],
        "chartPreviousClose": fech_anterior_janela,
        "previousClose": fech_anterior_dia,
        "fonte": FONTE,
        "simboloMt5": simbolo,
    }
    return {
        "meta": meta,
        "timestamp": epochs,
        "indicators": {
            "quote": [
                {
                    "open": [b["open"] for b in janela_barras],
                    "high": [b["high"] for b in janela_barras],
                    "low": [b["low"] for b in janela_barras],
                    "close": [b["close"] for b in janela_barras],
                    "volume": [b["volume"] for b in janela_barras],
                }
            ]
        },
    }


def _parametro(qs: dict[str, list[str]], nome: str, padrao: str) -> str:
    return (qs.get(nome) or [padrao])[0]


def resposta_para(url: str) -> dict | None:
    """Monta, com dados do MT5, o JSON que o Yahoo daria para esta URL.

    Devolve None se a URL não for do Yahoo ou se o MT5 não conseguir
    responder nenhum dos símbolos pedidos.
    """
    partes = urlparse(url)
    if "finance.yahoo.com" not in partes.netloc:
        return None
    qs = parse_qs(partes.query)
    intervalo = _parametro(qs, "interval", "1d")
    janela = _parametro(qs, "range", "1d")

    if "/finance/spark" in partes.path:
        simbolos = [s for s in _parametro(qs, "symbols", "").split(",") if s.strip()]
        resultado = []
        faltaram: dict[str, list[str]] = {}
        for s in simbolos:
            try:
                bloco = bloco_yahoo(s.strip(), intervalo, janela)
            except Mt5Indisponivel as e:
                faltaram.setdefault(str(e), []).append(s.strip())
                continue
            resultado.append({"symbol": s.strip(), "response": [bloco]})
        if faltaram:
            # Agrupado por motivo: uma linha legível mesmo com 30 símbolos.
            resumo = "; ".join(
                f"{', '.join(lista)} ({motivo})" for motivo, lista in faltaram.items()
            )
            logger.warning("MT5 sem dados para: %s", resumo[:400])
        if not resultado:
            return None
        return {"spark": {"result": resultado, "error": None}}

    if "/finance/chart/" in partes.path:
        simbolo = unquote(partes.path.rsplit("/", 1)[-1])
        try:
            bloco = bloco_yahoo(simbolo, intervalo, janela)
        except Mt5Indisponivel as e:
            logger.info("MT5 não atendeu %s: %s", simbolo, e)
            return None
        return {"chart": {"result": [bloco], "error": None}}

    return None


def interceptar(url: str) -> httpx.Response | None:
    """Ponto de entrada de `fetch_with_retry`.

    Devolve a resposta montada com o MT5, ou None para seguir ao Yahoo.
    Em modo exclusivo, levanta `httpx.ConnectError` em vez de seguir.
    """
    if not configurado() or "finance.yahoo.com" not in url:
        return None
    try:
        corpo = resposta_para(url)
    except Exception:  # noqa: BLE001 - falha do MT5 nunca derruba o coletor
        logger.exception("Erro ao montar resposta do MT5")
        corpo = None
    requisicao = httpx.Request("GET", url)
    if corpo is None:
        if em_modo_exclusivo():
            raise httpx.ConnectError("MT5 não respondeu", request=requisicao)
        return None
    registrar_fonte(FONTE)
    return httpx.Response(
        200, json=corpo, request=requisicao, headers={"X-Fonte": FONTE}
    )
