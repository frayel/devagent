"""Aceite da spec 167: os destaques do dia logo abaixo da manchete.

Sem rede: a função pura direto, e a página pela fixture `radares` da spec 155
com `app.main.get_highlights_view_data` trocado por um dict fixo.
"""

from __future__ import annotations

import re

from fastapi.testclient import TestClient

from app.main import app
from app.services.destaques import faixa
from app.services.highlights import format_asset
from devagent.aceite import exigir_spec_done
from tests.test_aceite_155 import T_1030, _faca, radares  # noqa: F401
from tests.test_aceite_150 import _snap

client = TestClient(app)

HIGHS = [
    {"ticker": "VALE3", "price": 61.4, "change_percent": 3.2141},
    {"ticker": "ITUB4", "price": 33.1, "change_percent": 1.02},
]
LOWS = [
    {"ticker": "MGLU3", "price": 9.87, "change_percent": -4.0493},
    {"ticker": "B3SA3", "price": 12.3, "change_percent": -0.5},
]


def _highlights(highs=HIGHS, lows=LOWS, em_revisao=()) -> dict:
    return {
        "highs": [format_asset(h) for h in highs],
        "lows": [format_asset(x) for x in lows],
        "em_revisao": [format_asset(r) for r in em_revisao],
        "time": "17/11/2026 10:30:12 BRT",
        "fonte": "yfinance",
        "up_count": 1,
        "down_count": 1,
        "total_count": 2,
        "neutral_count": 0,
        "dispersion_pct": 50.0,
        "titulo_altas": "Maiores altas",
        "titulo_baixas": "Maiores baixas",
        "pregao_data": None,
        "pregao": None,
        "ausentes_count": 0,
        "ausentes_tickers": [],
    }


def _linha(ticker: str, n: int) -> dict:
    return {"ticker": ticker, "radares": [f"R{i}" for i in range(n)]}


CONFLUENCIA = {
    "acoes": [_linha("PETR4", 3), _linha("VALE3", 3), _linha("ITUB4", 2)],
    "horario_texto": "17/11/2026 10:30 BRT",
}


def _texto(item: dict) -> str:
    return " ".join(str(v) for v in item.values() if v)


def _faixa_html(html: str) -> str:
    m = re.search(r'<nav class="[^"]*destaques-agora[^"]*".*?</nav>', html, re.S)
    assert m, "faixa ausente"
    return m.group(0)


def test_aceite_167_spec_done():
    exigir_spec_done("167")


def test_funcao_com_o_exemplo():
    itens = faixa(_highlights(), CONFLUENCIA, {"desatualizado": False}, None)
    assert len(itens) == 3
    alta, baixa, radar = itens
    assert alta["ticker"] == "VALE3" and alta["variacao"] == "+3,21%"
    assert baixa["ticker"] == "MGLU3" and baixa["variacao"] == "-4,05%"
    assert radar["ticker"] + radar["empate"] == "PETR4 e mais 1"
    assert radar["radares"] == "3 radares"
    assert [i["hora"] for i in itens] == ["10:30"] * 3
    assert [i["href"] for i in itens] == [
        "?aba=rankings",
        "?aba=rankings",
        "?aba=alertas",
    ]
    assert alta["title"] == "Fonte: yfinance · 17/11/2026 10:30:12 BRT"
    assert radar["title"] == "Fonte: os radares da aba Alertas · 17/11/2026 10:30 BRT"


def test_sem_alta_e_sem_baixa():
    h = _highlights(
        highs=[{"ticker": "B3SA3", "change_percent": -0.12}],
        lows=[{"ticker": "ITUB4", "change_percent": 0.0}],
    )
    alta, baixa = faixa(h, {"acoes": []}, None, None)
    assert alta["texto"] == "nenhuma ação em alta" and alta["href"] is None
    assert baixa["texto"] == "nenhuma ação em baixa" and baixa["href"] is None


def test_confluencia_vazia_e_highlights_ausente():
    itens = faixa(_highlights(), {"acoes": []}, None, None)
    assert [i["rotulo"] for i in itens] == ["Maior alta", "Maior baixa"]
    assert faixa(None, {"acoes": []}, None, None) == []


def test_sem_empate():
    conf = {"acoes": [_linha("PETR4", 3), _linha("VALE3", 2)], "horario_texto": ""}
    (radar,) = faixa(None, conf, None, None)
    assert "e mais" not in _texto(radar)
    assert radar["hora"] == ""


def test_data_historica_nos_links():
    itens = faixa(_highlights(), CONFLUENCIA, None, "2026-11-13")
    assert [i["href"] for i in itens] == [
        "?aba=rankings&data=2026-11-13",
        "?aba=rankings&data=2026-11-13",
        "?aba=alertas&data=2026-11-13",
    ]


def test_selo_desatualizado_so_em_alta_e_baixa(radares, monkeypatch):  # noqa: F811
    itens = faixa(_highlights(), CONFLUENCIA, {"desatualizado": True}, None)
    assert [i["desatualizado"] for i in itens] == [True, True, False]

    monkeypatch.setattr("app.main.get_highlights_view_data", _highlights)
    import app.main as main

    original = main._carimbos_criticos

    def carimbos(agora):
        c = original(agora)
        return {**c, "altas_baixas": {"desatualizado": True, "pregao_iso": None}}

    monkeypatch.setattr("app.main._carimbos_criticos", carimbos)
    html = _faixa_html(client.get("/").text)
    assert html.count("selo-desatualizado") == 2


def test_em_revisao_fica_fora():
    h = _highlights(em_revisao=[{"ticker": "OIBR3", "change_percent": 45.0}])
    assert "OIBR3" not in str(faixa(h, CONFLUENCIA, None, None))


def test_pagina_entre_manchete_e_abas(radares, monkeypatch):  # noqa: F811
    monkeypatch.setattr("app.main.get_highlights_view_data", _highlights)
    radares["volume_alerts"] = _snap(
        "volume_alerts", T_1030, [{"ticker": "PETR4", "ratio": 2.0, "price": 30.0}]
    )
    radares["faca_caindo"] = _snap("faca_caindo", T_1030, [_faca("PETR4")])
    html = client.get("/").text
    assert 'class="span-12 destaques-agora"' in html
    i = html.index("destaques-agora")
    assert html.index("manchete-texto") < i < html.index('id="abas-navegacao"')
    nav = re.sub(r"<[^>]+>", " ", _faixa_html(html))
    nav = re.sub(r"\s+", " ", nav)
    assert "Maior alta VALE3 ▲ +3,21% às 10:30" in nav
    assert "Maior baixa MGLU3 ▼ -4,05% às 10:30" in nav
    assert "Em mais radares PETR4 · 2 radares às 10:30" in nav


def test_pagina_sem_nada_sem_faixa(radares, monkeypatch):  # noqa: F811
    monkeypatch.setattr("app.main.get_highlights_view_data", lambda: None)
    assert "destaques-agora" not in client.get("/").text
