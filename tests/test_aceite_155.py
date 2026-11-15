"""Aceite da spec 155: as ações que vários radares apontam ao mesmo tempo.

O card "Em vários radares" conta, por ação, quantos radares com coleta em dia
a citam. Sem rede: os getters do banco são trocados por payloads fixos (o mapa
`GETTERS` da spec 150) e o relógio da página é congelado em 16/11/2026 10:45 BRT.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.radares import RADARES, confluencia
from devagent.aceite import exigir_spec_done
from tests.test_aceite_150 import AGORA, BRT, GETTERS, _historico, _snap

client = TestClient(app)


@pytest.fixture
def radares(monkeypatch):
    """Relógio em 10:45 BRT e os 20 radares frescos e vazios (como na spec 150)."""

    class Relogio(datetime):
        @classmethod
        def now(cls, tz=None):  # type: ignore[override]
            return AGORA if tz is None else AGORA.astimezone(tz)

    monkeypatch.setattr("app.main.datetime", Relogio)
    estado = {chave: _snap(chave, T_1030) for chave in GETTERS}
    for chave, (modulo, funcao) in GETTERS.items():
        monkeypatch.setattr(f"{modulo}.{funcao}", lambda *a, _c=chave, **k: estado[_c])
    return estado


T_1020 = datetime(2026, 11, 16, 10, 20, tzinfo=BRT)
T_1030 = datetime(2026, 11, 16, 10, 30, tzinfo=BRT)
T_1040 = datetime(2026, 11, 16, 10, 40, tzinfo=BRT)
T_1000 = datetime(2026, 11, 16, 10, 0, tzinfo=BRT)


def _faca(ticker: str) -> dict:
    return {"ticker": ticker, "dias": 4, "variacao_acumulada": -6.0}


def _exaustao(ticker: str) -> dict:
    return {"ticker": ticker, "queda_acumulada": -5.0, "recuperacao_intraday": 2.0}


def _exemplo(estado: dict) -> None:
    """O exemplo de ponta a ponta da spec, aplicado ao mapa de getters."""
    estado["volume_alerts"] = _snap(
        "volume_alerts",
        T_1030,
        [
            {"ticker": "PETR4", "ratio": 2.0, "price": 30.0},
            {"ticker": "VALE3", "ratio": 1.8, "price": 60.0},
        ],
    )
    estado["variacao_subita"] = _snap(
        "variacao_subita",
        T_1030,
        [
            {"ticker": "PETR4", "change_percent": 2.0},
            {"ticker": "MGLU3", "change_percent": -2.0},
            {"ticker": "petr4.SA", "change_percent": 2.0},
        ],
    )
    estado["exaustao_queda"] = _snap("exaustao_queda", T_1040, [_exaustao("MGLU3")])
    estado["faca_caindo"] = _snap("faca_caindo", T_1020, [_faca("PETR4")])
    estado["compradores_fundo"] = _snap(
        "compradores_fundo",
        T_1000,
        [{"ticker": "VALE3", "preco_atual": 60.0, "queda_maxima": -3.0}],
    )
    estado["scanner_capitulacao"] = None


def _contexto_exemplo() -> dict:
    """Payloads no formato do contexto de `index()`: dict com lista e timestamp."""
    vazio = {"timestamp": T_1030, "alertas": [], "alerts": []}
    ctx: dict = {chave: dict(vazio) for chave, _, _ in RADARES}
    ctx["volume_alerts"] = {
        "timestamp": T_1030,
        "alerts": [{"ticker": "PETR4"}, {"ticker": "VALE3"}],
    }
    ctx["variacao_subita"] = {
        "timestamp": T_1030,
        "alertas": [{"ticker": "PETR4"}, {"ticker": "MGLU3"}, {"ticker": "petr4.SA"}],
    }
    ctx["exaustao_queda"] = {"timestamp": T_1040, "alertas": [{"ticker": "MGLU3"}]}
    ctx["faca_caindo"] = {"timestamp": T_1020, "alertas": [{"ticker": "PETR4"}]}
    ctx["compradores_fundo"] = {"timestamp": T_1000, "alertas": [{"ticker": "VALE3"}]}
    ctx["scanner_capitulacao"] = None
    return ctx


def _card(html: str) -> str:
    m = re.search(
        r'<section class="painel span-12 [^"]*painel-confluencia[^"]*">.*?</section>',
        html,
        re.S,
    )
    assert m, "card Em vários radares ausente"
    return re.sub(r"<[^>]+>", " ", m.group(0))


def test_aceite_155_spec_done():
    exigir_spec_done("155")


def test_funcao_com_o_exemplo():
    r = confluencia(_contexto_exemplo(), AGORA, False)
    assert r["lidos"] == 18
    assert r["excedentes"] == 0
    assert [a["ticker"] for a in r["acoes"]] == ["PETR4", "MGLU3"]
    assert r["acoes"][0]["radares"] == [
        "Radar de volume",
        "Variação Súbita",
        "Radar de Faca Caindo",
    ]
    assert r["acoes"][1]["radares"] == ["Variação Súbita", "Exaustão de Queda"]
    assert r["horario"] == T_1020
    assert "10:20" in r["horario_texto"]


def test_item_objeto_conta_como_dict():
    from app.database import RadarCongestionamentoData

    ctx = _contexto_exemplo()
    ctx["radar_congestionamento"] = RadarCongestionamentoData(
        timestamp=T_1030,
        alertas_json=(
            '[{"ticker": "VALE3", "bandwidth": 1.0, "sparkline_path": "M0 0"}]'
        ),
        fonte="teste",
    )
    r = confluencia(ctx, AGORA, False)
    vale = [a for a in r["acoes"] if a["ticker"] == "VALE3"]
    assert vale and vale[0]["radares"] == [
        "Radar de volume",
        "Radar de Congestionamento",
    ]


def test_ts_sem_fuso_e_tratado_como_utc():
    ctx = _contexto_exemplo()
    ctx["exaustao_queda"]["timestamp"] = datetime(2026, 11, 16, 13, 18)  # sem fuso
    r = confluencia(ctx, AGORA, False)
    assert r["horario_texto"].endswith("10:18 BRT")


def test_pagina_com_o_exemplo(radares):
    _exemplo(radares)
    resp = client.get("/")
    assert resp.status_code == 200
    card = _card(resp.text)
    assert "Em vários radares" in card
    assert "PETR4" in card and "3 radares" in card
    assert "MGLU3" in card and "2 radares" in card
    assert "de 18 radares lidos agora" in card
    assert card.index("PETR4") < card.index("MGLU3")
    assert "VALE3" not in card
    assert "10:20" in card
    # O card vem antes dos cards dos radares.
    assert resp.text.index("painel-confluencia") < resp.text.index(">Radar de volume<")


def test_limite_de_dez_linhas(radares):
    tickers = [f"AAAA{i:02d}" for i in range(12)]
    itens = [{"ticker": t, "ratio": 2.0, "price": 10.0} for t in tickers]
    radares["volume_alerts"] = _snap("volume_alerts", T_1030, itens)
    radares["faca_caindo"] = _snap("faca_caindo", T_1030, [_faca(t) for t in tickers])
    html = client.get("/").text
    card = _card(html)
    assert html.count('<span class="confluencia-n">2 radares</span>') == 10
    assert "+2 ações em 2 radares" in card
    assert "AAAA09" in card and "AAAA10" not in card


def test_sem_confluencia_sem_card(radares):
    assert "Em vários radares" not in client.get("/").text
    radares["volume_alerts"] = _snap(
        "volume_alerts", T_1030, [{"ticker": "PETR4", "ratio": 2.0, "price": 30.0}]
    )
    radares["faca_caindo"] = _snap("faca_caindo", T_1030, [_faca("VALE3")])
    assert "Em vários radares" not in client.get("/").text


def test_data_historica_nao_descarta_por_idade(radares, monkeypatch):
    monkeypatch.setattr("app.main._get_seletor_context", _historico(monkeypatch))
    _exemplo(radares)
    tres_horas = timedelta(hours=3)
    for snap in radares.values():
        if snap is not None:
            snap.timestamp = snap.timestamp - tres_horas
    card = _card(client.get("/").text)
    assert "VALE3" in card
    linha = re.search(r"VALE3\s+(\d+) radares", card)
    assert linha and linha.group(1) == "2"


def test_snapshot_traz_a_confluencia(radares):
    _exemplo(radares)
    painel = client.get("/api/snapshot").json()["paineis"]["confluencia_radares"]
    assert [a["ticker"] for a in painel["acoes"]] == ["PETR4", "MGLU3"]
    assert painel["lidos"] == 18
    assert painel["excedentes"] == 0
    assert painel["horario"].startswith("2026-11-16T")


def test_snapshot_sem_confluencia(radares):
    painel = client.get("/api/snapshot").json()["paineis"]["confluencia_radares"]
    assert painel["acoes"] == []
    assert painel["lidos"] == 20
    assert painel["horario"] is None
