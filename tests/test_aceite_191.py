"""Aceite da spec 191: o Consultor escreve preços, potenciais e datas no padrão brasileiro.

Sem rede: os filtros são funções puras; a página é montada com um dublê de
`calcular_consultor`, no molde de `tests/test_aceite_190.py`.
"""

from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient

import app.main
from app.consultor.formato import data_brasilia, percentual, reais
from app.main import app as fastapi_app
from devagent.aceite import exigir_spec_done


@pytest.fixture(autouse=True)
def _so_com_spec_done():
    exigir_spec_done("191")


@pytest.mark.parametrize(
    ("bruto", "exibido"),
    [
        (45.0, "R$ 45,00"),
        ("R$ 45,00", "R$ 45,00"),
        ("52.5", "R$ 52,50"),
        ("R$ 1.234,50", "R$ 1.234,50"),
        (1234.5, "R$ 1.234,50"),
        (None, "-"),
        ("", "-"),
        ("sem alvo", "-"),
    ],
)
def test_reais(bruto, exibido):
    assert reais(bruto) == exibido


@pytest.mark.parametrize(
    ("bruto", "exibido"),
    [(0.12345, "+12,3%"), (-0.05, "-5,0%"), (0.0, "+0,0%"), (None, "-")],
)
def test_percentual(bruto, exibido):
    assert percentual(bruto) == exibido


@pytest.mark.parametrize(
    ("bruto", "exibido"),
    [
        ("2026-11-15T23:30:00+00:00", "15/11/2026"),
        ("2026-11-16T01:30:00+00:00", "15/11/2026"),
        ("2026-11-16", "15/11/2026"),
        (None, "-"),
        ("lixo", "-"),
    ],
)
def test_data_brasilia(bruto, exibido):
    assert data_brasilia(bruto) == exibido


def _opiniao(alvo, rotulo):
    return {
        "ticker": "PETR4",
        "casa": f"Casa {rotulo}",
        "recomendacao": "compra",
        "preco_alvo": alvo,
        "resumo": f"resumo {rotulo}",
        "data_materia": "2026-11-16T01:30:00+00:00",
        "link": f"https://exemplo.invalid/191-{rotulo}",
        "alvo_situacao": None,
    }


def _item(ticker, fechamento, consenso):
    return {
        "ticker": ticker,
        "fechamento": fechamento,
        "regra": "Regra de teste",
        "motivo": "",
        "gatilho": "",
        "decisao_tecnica": "Comprar",
        "justificativa": "",
        "mensagem_confianca": "confiança de teste",
        "consenso": consenso,
        "consenso_yahoo": None,
    }


def test_pagina_no_padrao_brasileiro(monkeypatch):
    monkeypatch.delenv("CONSULTOR_SENHA", raising=False)
    opinioes = [_opiniao("52.5", "a"), _opiniao(45.0, "b")]
    linha = {
        "ticker": "PETR4",
        "opinioes_texto": "2 compra",
        "cobertura_insuficiente": False,
        "alvo_min": 45.0,
        "alvo_max": 52.5,
        "mais_recente_data": "2026-11-16T01:30:00+00:00",
        "mais_recente_casa": "Casa a",
        "opinioes": opinioes,
    }
    consenso = {"consenso": "compra", "preco_alvo_mediano": 45.0, "potencial": 0.12345}
    sem_sinal = _item("VALE3", 32.1, {"consenso": "cobertura insuficiente"})
    sem_sinal["decisao_tecnica"] = "Sem sinal"

    def mock_calc():
        return {
            "resultados": {
                "Comprar": [_item("ITUB4", 1234.5, consenso)],
                "Vender": [],
                "Aguardar": [],
                "No radar": [],
                "Sem sinal": [sem_sinal],
            },
            "opinioes_recentes": opinioes,
            "opinioes_por_ativo": [linha],
            "opinioes_status": {
                "status": "ok",
                "motivo": "",
                "desde": "",
                "ultima_extracao_em": "2026-11-21T10:00:00+00:00",
                "materias_processadas": 2,
                "opinioes_gravadas": 2,
                "descartadas": 0,
            },
            "ativos_avaliados": 2,
        }

    monkeypatch.setattr(app.main, "calcular_consultor", mock_calc)
    resposta = TestClient(fastapi_app).get("/consultor")
    assert resposta.status_code == 200
    html = resposta.text

    for trecho in (
        "R$ 52,50",
        "R$ 45,00",
        "15/11/2026",
        "R$ 1.234,50",
        "(+12,3%)",
        "R$ 32,10",
        "R$ 45,00 a R$ 52,50",
    ):
        assert trecho in html, trecho
    assert not re.search(r"R\$ \d+\.\d{2}\b", html)
    assert "R$ R$" not in html
    inicio = html.index("Opiniões Recentes")
    assert "2026-11-16" not in html[inicio:]
