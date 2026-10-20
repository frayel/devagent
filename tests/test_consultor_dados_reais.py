"""O Consultor lê a série diária no formato que o coletor grava.

Os testes da página mockam `calcular_consultor`; este cobre o caminho real
coletor → cache → calculador, que ficou quebrado em produção.
"""

import json
from datetime import datetime, timezone

import httpx

from app.collectors import consultor_historico
from app.collectors.utils import simbolo_yahoo
from app.consultor.calculador import calcular_consultor
from app.consultor.universo import CARTEIRA_IBOVESPA


def _serie(inicio: float, passo: float, n: int = 300) -> dict:
    t0 = 1_700_000_000
    closes = [inicio + passo * i for i in range(n)]
    return {
        "chart": {
            "result": [
                {
                    "timestamp": [t0 + 86400 * i for i in range(n)],
                    "indicators": {
                        "quote": [
                            {
                                "close": closes,
                                "volume": [1_000_000] * n,
                                "open": closes,
                                "high": closes,
                                "low": closes,
                            }
                        ]
                    },
                }
            ]
        }
    }


def test_simbolo_yahoo():
    assert simbolo_yahoo("PETR4") == "PETR4.SA"
    assert simbolo_yahoo("^BVSP") == "^BVSP"
    assert simbolo_yahoo("BRL=X") == "BRL=X"
    assert simbolo_yahoo("VALE3.SA") == "VALE3.SA"


def test_coletor_alimenta_calculador(monkeypatch):
    pedidos = []

    def fetch(url, client=None, **kw):
        pedidos.append(url)
        simbolo = url.split("/chart/")[1].split("?")[0]
        corpo = _serie(100_000, 50) if simbolo == "^BVSP" else _serie(20, 0.05)
        return httpx.Response(200, json=corpo, request=httpx.Request("GET", url))

    monkeypatch.setattr("app.collectors.utils.fetch_with_retry", fetch)

    assert consultor_historico.collect_and_save() is True
    assert any("/chart/^BVSP?" in u for u in pedidos)
    assert not any("^BVSP.SA" in u for u in pedidos)

    dados = calcular_consultor()
    assert dados["ativos_avaliados"] == len(CARTEIRA_IBOVESPA)
    avaliados = [
        item
        for grupo in dados["resultados"].values()
        for item in grupo
        if item["motivo"] != "Sem dados"
    ]
    assert len(avaliados) == len(CARTEIRA_IBOVESPA)
    assert all(item["fechamento"] > 0 for item in avaliados)
    json.dumps(dados, default=str)  # a página e a API serializam o resultado

    # Segunda rodada dentro da hora usa o cache, sem pedir de novo.
    antes = len(pedidos)
    consultor_historico.collect_and_save()
    assert len(pedidos) == antes


def test_pagina_consultor_mostra_ativos(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app

    def fetch(url, client=None, **kw):
        simbolo = url.split("/chart/")[1].split("?")[0]
        corpo = _serie(100_000, 50) if simbolo == "^BVSP" else _serie(20, 0.05)
        return httpx.Response(200, json=corpo, request=httpx.Request("GET", url))

    monkeypatch.setattr("app.collectors.utils.fetch_with_retry", fetch)
    monkeypatch.delenv("CONSULTOR_SENHA", raising=False)
    consultor_historico.collect_and_save()

    resp = TestClient(app).get("/consultor")
    assert resp.status_code == 200
    assert "Dados do consultor indisponíveis" not in resp.text
    assert CARTEIRA_IBOVESPA[0] in resp.text


def test_calculador_le_bloco_gravado_no_cache():
    from app.database import save_historico_diario

    agora = datetime.now(timezone.utc)
    for t in ("^BVSP", *CARTEIRA_IBOVESPA[:2]):
        bloco = _serie(100, 1)["chart"]["result"][0]
        save_historico_diario(t, "2y", "1d", json.dumps(bloco), agora)
    dados = calcular_consultor()
    assert dados["resultados"]
