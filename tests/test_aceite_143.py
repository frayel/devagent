"""Aceite da spec 143: o fator peso pesado explica o sinal da conta."""

from __future__ import annotations

import logging
import re

import pytest
import respx
from fastapi.testclient import TestClient

from app.collectors import fator_peso_pesado
from app.collectors.fator_peso_pesado import TICKERS_PESO
from app.database import get_latest_fator_peso_pesado_data
from app.main import app
from devagent.aceite import exigir_spec_done

client = TestClient(app)
CHART = "https://{sub}.finance.yahoo.com/v8/finance/chart/{ticker}?range=1d&interval=1d"
IBOV_PREV = 130_000.0
RAZAO = re.compile(r"[+−-]?\d+(?:,\d+)?%")


def test_aceite_143_spec_done():
    exigir_spec_done("143")


def _chart(preco: float | None, anterior: float) -> dict:
    meta = {"regularMarketPrice": preco, "previousClose": anterior}
    return {"chart": {"result": [{"meta": meta}]}}


def _mock(ticker: str, preco: float | None, anterior: float) -> None:
    for sub in ("query1", "query2"):
        respx.get(CHART.format(sub=sub, ticker=ticker)).respond(
            json=_chart(preco, anterior)
        )


def _coletar(ibov_atual: float, pontos: dict[str, float], sem_preco: str = ""):
    """Cada ticker rende os pontos pedidos: pts = var% × peso / 100 × IBOV_PREV."""
    with respx.mock:
        _mock("^BVSP", ibov_atual, IBOV_PREV)
        for ticker, peso in TICKERS_PESO.items():
            pts = pontos.get(ticker, 0.0)
            var_pct = pts / (peso / 100 * IBOV_PREV) * 100
            preco = None if ticker == sem_preco else 100.0 * (1 + var_pct / 100)
            _mock(ticker, preco, 100.0)
        return fator_peso_pesado.collect_and_save()


def _card() -> str:
    html = client.get("/").text
    m = re.search(
        r"<section[^>]*>\s*<div class=\"cab\">\s*<h2>Fator Peso Pesado</h2>.*?</section>",
        html,
        re.S,
    )
    assert m, "card Fator Peso Pesado não encontrado"
    return m.group(0)


def _valor(card: str) -> str:
    m = re.search(r'<div class="valor num">(.*?)</div>', card, re.S)
    assert m
    return m.group(1).strip()


def test_sentido_oposto():
    assert _coletar(131_000.0, {"VALE3.SA": -508.0}) is True
    card = _card()
    assert _valor(card) == "−50,8%"
    assert "sentido oposto" in card
    assert "limitado" not in card


def test_acima_de_100_nao_corta():
    assert _coletar(131_000.0, {"VALE3.SA": 1_000.0, "PETR4.SA": 500.0}) is True
    card = _card()
    assert _valor(card) in ("+150,0%", "+150%")
    assert "compensou" in card
    assert "100%" not in _valor(card)
    assert "limitado" not in card


def test_teto_visivel():
    assert _coletar(131_000.0, {"VALE3.SA": 8_000.0}) is True
    snap = client.get("/api/snapshot").json()["paineis"]["fator_peso_pesado"]
    assert snap["proporcao_bruta"] == pytest.approx(800.0, abs=0.01)
    assert snap["proporcao"] == 500.0
    assert snap["limitado"] is True
    assert "limitado" in _card()


def test_mercado_lateral_sem_razao():
    assert _coletar(130_065.0, {"VALE3.SA": 500.0}) is True
    card = _card()
    assert "Mercado lateral" in card
    assert not RAZAO.search(_valor(card))
    assert not RAZAO.search(card.split('class="valor num"', 1)[1])
    snap = client.get("/api/snapshot").json()["paineis"]["fator_peso_pesado"]
    assert snap["proporcao"] == 0.0


def test_falta_um_nome_fica_indisponivel(caplog):
    with caplog.at_level(logging.WARNING):
        ok = _coletar(131_000.0, {"VALE3.SA": 500.0}, sem_preco="PETR3.SA")
    assert ok is False
    assert get_latest_fator_peso_pesado_data() is None
    card = _card()
    assert "indisponível" in card
    assert not RAZAO.search(card.split("</h2>", 1)[1].split("vazio", 1)[1])
    assert "PETR3" in caplog.text


def test_pesos_somam_34():
    assert sum(TICKERS_PESO.values()) == 34.0
    assert TICKERS_PESO == {
        "VALE3.SA": 12.0,
        "PETR4.SA": 8.0,
        "ITUB4.SA": 7.0,
        "PETR3.SA": 4.0,
        "BBAS3.SA": 3.0,
    }
