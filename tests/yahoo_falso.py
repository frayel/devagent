"""Yahoo Finance falso e determinístico para testes ponta a ponta.

Responde às rotas `v7/finance/spark` e `v8/finance/chart` com séries
sintéticas, no mesmo formato da API real, para qualquer símbolo. A forma da
série depende do símbolo (hash estável), então o mesmo ticker sempre cai, sobe
ou oscila do mesmo jeito e todos os painéis recebem casos interessantes:
quedas consecutivas, altas, picos de volume, rally do Ibovespa.

Qualquer outra URL (brapi, por exemplo) responde 404, e os coletores caem
para o Yahoo como fariam em produção sem token.

Uso: `instalar(monkeypatch)` dentro de um teste.
"""

from __future__ import annotations

import zlib
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, unquote, urlparse

import httpx

_PREGOES = {
    "1d": 1,
    "2d": 2,
    "5d": 5,
    "10d": 10,
    "15d": 15,
    "1mo": 22,
    "2mo": 42,
    "3mo": 63,
    "6mo": 126,
    "1y": 252,
    "2y": 504,
}


def _semente(simbolo: str) -> int:
    return zlib.crc32(simbolo.encode())


def _fechamentos(simbolo: str, n: int) -> list[float]:
    """Série de `n` fechamentos com forma escolhida pelo símbolo.

    Formas: 0 queda contínua, 1 alta contínua, 2 zigue-zague, 3 queda e
    depois recuperação. O Ibovespa sempre sobe forte nos últimos pregões, para
    que os painéis que dependem de rally tenham o que mostrar.
    """
    s = _semente(simbolo)
    if simbolo in ("^BVSP", "%5EBVSP"):
        # Sobe 1,4% e cai 0,4% em dias alternados: rally nos últimos
        # pregões e dias de queda para os painéis defensivos.
        valores, v = [], 120_000.0
        for i in range(n + 1):
            v *= 1.014 if i % 2 else 0.996
            valores.append(round(v, 2))
        return valores
    elif simbolo == "BRL=X":
        base, forma = 5.2, 2
    elif "TICKER" in simbolo or simbolo == "PETR4.SA":
        base, forma = 10.0 + s % 50, 0
    else:
        base, forma = 10.0 + s % 50, s % 4
    total = n + 1  # um pregão a mais vira o fechamento anterior
    valores = []
    for i in range(total):
        resto = total - 1 - i  # pregões até o último
        if forma == 0:
            fator = 1 + 0.012 * resto
        elif forma == 1:
            fator = 1 - 0.008 * resto
        elif forma == 2:
            fator = 1 + (0.01 if i % 2 else -0.01)
        else:
            fator = 1 + 0.004 * abs(resto - total // 2)
        valores.append(round(base * fator, 2))
    return valores


def _resultado(simbolo: str, intervalo_range: str, intervalo: str) -> dict:
    n = _PREGOES.get(intervalo_range, 22)
    if intervalo != "1d":
        n = 26  # intradiário: 26 barras de 15 min
    serie = _fechamentos(simbolo, n)
    anterior, fechamentos = serie[0], serie[1:]
    agora = datetime.now(timezone.utc).replace(hour=19, minute=0, second=0)
    passo = timedelta(days=1) if intervalo == "1d" else timedelta(minutes=15)
    tempos = [int((agora - passo * (n - 1 - i)).timestamp()) for i in range(n)]
    s = _semente(simbolo)
    volumes = [1_000_000 + (s % 7) * 100_000 for _ in range(n)]
    if s % 3 == 0 or "TICKER" in simbolo or simbolo == "PETR4.SA":
        volumes[-1] *= 4  # pico de volume no último pregão
    ultimo = fechamentos[-1]
    return {
        "meta": {
            "symbol": simbolo,
            "currency": "BRL",
            "regularMarketPrice": ultimo,
            "chartPreviousClose": anterior,
            "previousClose": anterior,
            "regularMarketDayLow": round(ultimo * 0.97, 2),
            "regularMarketDayHigh": round(ultimo * 1.01, 2),
            "regularMarketVolume": volumes[-1],
            "regularMarketTime": tempos[-1],
        },
        "timestamp": tempos,
        "indicators": {
            "quote": [
                {
                    "open": [round(v * 1.005, 2) for v in fechamentos],
                    "high": [round(v * 1.01, 2) for v in fechamentos],
                    "low": [round(v * 0.97, 2) for v in fechamentos],
                    "close": fechamentos,
                    "volume": volumes,
                }
            ]
        },
    }


def responder(request: httpx.Request) -> httpx.Response:
    url = urlparse(str(request.url))
    q = parse_qs(url.query)
    intervalo_range = q.get("range", ["1mo"])[0]
    intervalo = q.get("interval", ["1d"])[0]
    if "finance.yahoo.com" in url.netloc and "/v7/finance/spark" in url.path:
        simbolos = unquote(q.get("symbols", [""])[0]).split(",")
        corpo = {
            "spark": {
                "result": [
                    {
                        "symbol": s,
                        "response": [_resultado(s, intervalo_range, intervalo)],
                    }
                    for s in simbolos
                    if s
                ],
                "error": None,
            }
        }
        return httpx.Response(200, json=corpo, request=request)
    if "finance.yahoo.com" in url.netloc and "/v8/finance/chart/" in url.path:
        simbolo = unquote(url.path.rsplit("/", 1)[-1])
        corpo = {
            "chart": {
                "result": [_resultado(simbolo, intervalo_range, intervalo)],
                "error": None,
            }
        }
        return httpx.Response(200, json=corpo, request=request)
    return httpx.Response(404, json={"error": "fora do Yahoo falso"}, request=request)


def instalar(monkeypatch) -> None:
    """Desvia todo o tráfego httpx dos coletores para o Yahoo falso."""
    from app.collectors import utils

    enviar_original = httpx.Client.send

    def enviar(self, request, *args, **kwargs):
        # O TestClient do FastAPI também é um httpx.Client: a página passa.
        if request.url.host == "testserver":
            return enviar_original(self, request, *args, **kwargs)
        return responder(request)

    monkeypatch.setattr(httpx.Client, "send", enviar)
    monkeypatch.setattr(utils, "_enforce_rate_limit", lambda dominio: None)
    monkeypatch.setattr(utils.time, "sleep", lambda s: None)
