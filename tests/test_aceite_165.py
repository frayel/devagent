"""Aceite da spec 165: Opiniões Recentes com uma linha por ativo.

Sem rede: as funções puras recebem o exemplo da spec com a referência fixa,
e a página lê opiniões gravadas no SQLite temporário do `conftest.py`, com
`calcular_consultor` trocado por uma função (o molde de `test_consultor.py`).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

import app.main
from app.consultor import armazenamento
from app.consultor.sintese import agrupar_por_ativo, calcular_consenso, ultima_por_casa
from app.main import app as fastapi_app
from app.services.consultor_opinioes import save_opiniao
from devagent.aceite import exigir_spec_done

REFERENCIA = datetime(2026, 11, 16, 12, 0, tzinfo=timezone.utc)


def _op(rotulo, casa, ticker, rec, alvo, data, link=None):
    return {
        "rotulo": rotulo,
        "casa": casa,
        "ticker": ticker,
        "recomendacao": rec,
        "preco_alvo": alvo,
        "data_materia": data,
        "link": link or f"https://exemplo.invalid/{rotulo}",
        "resumo": f"resumo {rotulo}",
    }


EXEMPLO = [
    _op("a", "BTG Pactual", "PETR4", "compra", "R$ 45,00", "2026-11-14T13:00:00+00:00"),
    _op("b", "BTG Pactual", "PETR4", "neutro", None, "2026-11-01T12:00:00+00:00"),
    _op("c", "XP", "PETR4", "compra", "38", "2026-11-10T12:00:00+00:00"),
    _op("d", "Itaú BBA", "PETR4", "compra", None, "2026-11-12T10:00:00+00:00"),
    _op("e", "Itaú BBA", "PETR4", "compra", None, "2026-11-12T14:00:00+00:00"),
    _op("f", "Safra", "VALE3", "venda", "52,00", "2026-11-12T12:00:00+00:00"),
    _op("g", "Genial", "ITUB4", "compra", "40", "2026-10-10T12:00:00+00:00"),
]


@pytest.fixture(autouse=True)
def _so_com_spec_done():
    exigir_spec_done("165")


def test_agrupar_por_ativo_exemplo_da_spec():
    linhas = agrupar_por_ativo(EXEMPLO, referencia=REFERENCIA)
    assert [linha["ticker"] for linha in linhas] == ["PETR4", "VALE3"]
    petr, vale = linhas

    assert petr["contagem"] == {"compra": 3, "neutro": 0, "venda": 0}
    assert petr["opinioes_texto"] == "3 Comprar"
    assert petr["cobertura_insuficiente"] is False
    assert (petr["alvo_min"], petr["alvo_max"]) == (38.0, 45.0)
    assert petr["mais_recente_casa"] == "BTG Pactual"
    assert [op["rotulo"] for op in petr["opinioes"]] == ["a", "e", "d", "c", "b"]

    assert vale["contagem"] == {"compra": 0, "neutro": 0, "venda": 1}
    assert vale["opinioes_texto"] == "1 Vender"
    assert vale["cobertura_insuficiente"] is True
    assert (vale["alvo_min"], vale["alvo_max"]) == (52.0, 52.0)
    assert vale["mais_recente_casa"] == "Safra"
    assert len(vale["opinioes"]) == 1


def test_contagem_igual_ao_total_do_consenso():
    for linha in agrupar_por_ativo(EXEMPLO, referencia=REFERENCIA):
        do_ticker = [op for op in EXEMPLO if op["ticker"] == linha["ticker"]]
        consenso = calcular_consenso(do_ticker, REFERENCIA)
        if consenso["consenso"] != "cobertura insuficiente":
            assert sum(linha["contagem"].values()) == consenso["detalhes"]["total"]
        else:
            assert linha["cobertura_insuficiente"] is True


def test_ultima_por_casa_petr4():
    petr = [op for op in EXEMPLO if op["ticker"] == "PETR4"]
    casas = ultima_por_casa(petr, REFERENCIA)
    assert set(casas) == {"BTG Pactual", "XP", "Itaú BBA"}
    assert casas["BTG Pactual"]["rotulo"] == "a"


def _gravar(guid, ticker, casa, rec, alvo, data):
    save_opiniao(
        guid=guid,
        ticker=ticker,
        casa=casa,
        recomendacao=rec,
        preco_alvo=alvo,
        resumo="resumo",
        trecho="trecho",
        data_materia=data,
        link=f"https://exemplo.invalid/{guid}",
    )


def _pagina(monkeypatch, opinioes, referencia=None):
    monkeypatch.delenv("CONSULTOR_SENHA", raising=False)

    def mock_calc():
        return {
            "resultados": {
                "Comprar": [],
                "Vender": [],
                "Aguardar": [],
                "No radar": [],
                "Sem sinal": [],
            },
            "opinioes_recentes": opinioes,
            "opinioes_por_ativo": agrupar_por_ativo(opinioes, referencia=referencia),
            "opinioes_status": {
                "status": "ok",
                "motivo": "",
                "desde": "",
                "ultima_extracao_em": "2026-11-16T10:00:00+00:00",
                "materias_processadas": 3,
                "opinioes_gravadas": len(opinioes),
                "descartadas": 0,
            },
            "ativos_avaliados": 0,
        }

    monkeypatch.setattr(app.main, "calcular_consultor", mock_calc)
    resposta = TestClient(fastapi_app).get("/consultor")
    assert resposta.status_code == 200
    return resposta.text


def test_pagina_uma_linha_por_ativo(monkeypatch):
    armazenamento.init_db()
    ontem = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    _gravar("aceite-165-1", "PETR4", "Casa A 165", "compra", 40.0, ontem)
    _gravar("aceite-165-2", "PETR4", "Casa B 165", "compra", None, ontem)
    _gravar("aceite-165-3", "VALE3", "Casa C 165", "venda", 52.0, ontem)
    opinioes = [
        op
        for ops in armazenamento.get_opinioes_ativos().values()
        for op in ops
        if op["guid"].startswith("aceite-165-")
    ]
    assert len(opinioes) == 3

    html = _pagina(monkeypatch, opinioes)
    assert html.count('<details class="opiniao-ativo">') == 2
    assert "2 Comprar" in html
    assert "1 Vender · cobertura insuficiente" in html
    for n in (1, 2, 3):
        assert html.count(f'href="https://exemplo.invalid/aceite-165-{n}"') == 1


def test_sem_opinioes_mostra_diagnostico(monkeypatch):
    html = _pagina(monkeypatch, [])
    assert '<details class="opiniao-ativo">' not in html
    assert (
        "Nenhuma matéria das fontes citou ativos do Ibovespa com opinião de casa "
        "de análise nos últimos 30 dias." in html
    )


def test_dia_no_fuso_de_brasilia(monkeypatch):
    opinioes = [
        _op("z", "Casa Z", "WEGE3", "compra", None, "2026-11-15T01:00:00+00:00"),
    ]
    html = _pagina(monkeypatch, opinioes, referencia=REFERENCIA)
    inicio = html.index('<details class="opiniao-ativo">')
    summary = html[inicio : html.index("</summary>", inicio)]
    assert "14/11 · Casa Z" in summary
    assert "15/11" not in summary
