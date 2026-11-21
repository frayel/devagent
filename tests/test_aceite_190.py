"""Aceite da spec 190: cada opinião com preço-alvo diz se o alvo já foi atingido.

Sem rede: a função pura recebe o exemplo da spec; `get_fechamentos` lê o
SQLite temporário do `conftest.py`, semeado por `INSERT` direto; a página
segue o molde de `tests/test_aceite_165.py`.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

import app.main
from app.consultor import armazenamento
from app.consultor.sintese import agrupar_por_ativo, situacao_do_alvo
from app.main import app as fastapi_app
from app.services.consultor_opinioes import save_opiniao
from devagent.aceite import exigir_spec_done

PETR4 = [
    ("2026-11-10", 40.00),
    ("2026-11-11", 41.00),
    ("2026-11-12", 42.50),
    ("2026-11-13", 44.00),
    ("2026-11-16", 45.20),
    ("2026-11-17", 44.80),
    ("2026-11-18", 43.90),
    ("2026-11-19", 44.10),
]
VALE3 = [
    ("2026-11-11", 60.00),
    ("2026-11-12", 58.00),
    ("2026-11-13", 55.00),
    ("2026-11-16", 53.10),
    ("2026-11-17", 51.90),
    ("2026-11-18", 52.40),
    ("2026-11-19", 52.80),
]
FECHAMENTOS = {"PETR4": PETR4, "VALE3": VALE3}

LINHA_METODO = (
    "Até o alvo: compara o preço-alvo com os fechamentos guardados pelo Consultor "
    'desde o dia da matéria. "Atingido" é o primeiro fechamento que chegou ao alvo, '
    "no sentido do fechamento anterior à matéria."
)


def _op(rotulo, casa, ticker, rec, alvo, data):
    return {
        "rotulo": rotulo,
        "casa": casa,
        "ticker": ticker,
        "recomendacao": rec,
        "preco_alvo": alvo,
        "data_materia": data,
        "link": f"https://exemplo.invalid/190-{rotulo}",
        "resumo": f"resumo {rotulo}",
    }


OPS = {
    "a": _op(
        "a", "BTG Pactual", "PETR4", "compra", "R$ 45,00", "2026-11-12T01:00:00+00:00"
    ),
    "b": _op("b", "XP", "PETR4", "compra", 50.0, "2026-11-17T12:00:00+00:00"),
    "c": _op("c", "Ágora", "PETR4", "venda", 42, "2026-11-19T20:00:00+00:00"),
    "d": _op("d", "Itaú BBA", "PETR4", "neutro", None, "2026-11-18T12:00:00+00:00"),
    "e": _op("e", "Safra", "VALE3", "venda", "52,00", "2026-11-12T15:00:00+00:00"),
    "f": _op("f", "Genial", "ITUB4", "compra", 40, "2026-11-18T12:00:00+00:00"),
    "g": _op("g", "Safra", "PETR4", "compra", 48, "2026-11-10T13:00:00+00:00"),
}

ESPERADO = {
    "a": ("atingido", "alta", "2026-11-16", 45.20, None),
    "b": ("falta", "alta", "2026-11-19", 44.10, 0.13379),
    "c": ("falta", "baixa", "2026-11-19", 44.10, -0.04762),
    "e": ("atingido", "baixa", "2026-11-17", 51.90, None),
}


@pytest.fixture(autouse=True)
def _so_com_spec_done():
    exigir_spec_done("190")


@pytest.mark.parametrize("rotulo", sorted(OPS))
def test_situacao_do_alvo_exemplo_da_spec(rotulo):
    op = OPS[rotulo]
    situacao = situacao_do_alvo(op, FECHAMENTOS.get(op["ticker"], []))
    if rotulo not in ESPERADO:
        assert situacao is None
        return
    estado, sentido, data, preco, distancia = ESPERADO[rotulo]
    assert situacao is not None
    assert situacao["estado"] == estado
    assert situacao["sentido"] == sentido
    assert situacao["data"] == data
    assert situacao["preco"] == pytest.approx(preco)
    if distancia is None:
        assert "distancia" not in situacao
    else:
        assert situacao["distancia"] == pytest.approx(distancia, abs=1e-4)


def test_base_da_opiniao_a_e_do_dia_anterior_em_brasilia():
    situacao = situacao_do_alvo(OPS["a"], PETR4)
    assert situacao is not None
    assert (situacao["base_data"], situacao["base_preco"]) == ("2026-11-10", 40.0)


def test_alvo_igual_a_base_nao_tem_sentido():
    op = _op("h", "Casa H", "PETR4", "neutro", "44,10", "2026-11-20T12:00:00+00:00")
    assert situacao_do_alvo(op, PETR4) is None


def test_corte_em_13_11():
    cortado = {
        t: [(d, p) for d, p in lista if d <= "2026-11-13"]
        for t, lista in FECHAMENTOS.items()
    }
    a = situacao_do_alvo(OPS["a"], cortado["PETR4"])
    e = situacao_do_alvo(OPS["e"], cortado["VALE3"])
    assert a is not None and e is not None
    assert a["estado"] == e["estado"] == "falta"
    assert a["distancia"] == pytest.approx(0.02273, abs=1e-4)
    assert e["distancia"] == pytest.approx(-0.05455, abs=1e-4)


def _semear_fechamentos():
    armazenamento.init_db()
    conn, backend = armazenamento.get_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM consultor_fechamentos")
        for ticker, lista in FECHAMENTOS.items():
            for data, preco in lista:
                cur.execute(
                    armazenamento.sql_para(
                        backend,
                        "INSERT INTO consultor_fechamentos (data_pregao, ticker, preco_fechamento) VALUES (?, ?, ?)",
                    ),
                    (data, ticker, preco),
                )
        conn.commit()
    finally:
        conn.close()


def test_get_fechamentos():
    _semear_fechamentos()
    lidos = armazenamento.get_fechamentos(["PETR4", "VALE3", "ITUB4"])
    assert lidos == {"PETR4": PETR4, "VALE3": VALE3}
    cortado = armazenamento.get_fechamentos(
        ["PETR4", "VALE3", "ITUB4"], ate="2026-11-13"
    )
    assert cortado["PETR4"][-1][0] == "2026-11-13"
    assert armazenamento.get_fechamentos([]) == {}


def test_agrupar_por_ativo_copia_com_alvo_situacao():
    entrada = [OPS[r] for r in "abcd"]
    referencia = datetime(2026, 11, 21, 12, 0, tzinfo=timezone.utc)
    linhas = agrupar_por_ativo(entrada, referencia=referencia, fechamentos=FECHAMENTOS)
    opinioes = [op for linha in linhas for op in linha["opinioes"]]
    assert len(opinioes) == 4
    por_rotulo = {op["rotulo"]: op for op in opinioes}
    assert por_rotulo["a"]["alvo_situacao"]["estado"] == "atingido"
    assert por_rotulo["d"]["alvo_situacao"] is None
    assert all("alvo_situacao" not in op for op in entrada)

    sem = agrupar_por_ativo(entrada, referencia=referencia)
    assert all(op["alvo_situacao"] is None for linha in sem for op in linha["opinioes"])


def _pagina(monkeypatch, opinioes_por_ativo, opinioes):
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
            "opinioes_por_ativo": opinioes_por_ativo,
            "opinioes_status": {
                "status": "ok",
                "motivo": "",
                "desde": "",
                "ultima_extracao_em": "2026-11-21T10:00:00+00:00",
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


def test_pagina_mostra_ate_o_alvo(monkeypatch):
    armazenamento.init_db()
    for r in "abc":
        op = OPS[r]
        save_opiniao(
            guid=f"aceite-190-{r}",
            ticker=op["ticker"],
            casa=op["casa"],
            recomendacao=op["recomendacao"],
            preco_alvo=op["preco_alvo"],
            resumo=op["resumo"],
            trecho="trecho",
            data_materia=op["data_materia"],
            link=op["link"],
        )
    _semear_fechamentos()
    referencia = datetime(2026, 11, 21, 12, 0, tzinfo=timezone.utc)
    # Lidas por guid, não por janela: o teste não depende do relógio real.
    conn, backend = armazenamento.get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            armazenamento.sql_para(
                backend,
                "SELECT guid, ticker, casa, recomendacao, preco_alvo, resumo, "
                "data_materia, link FROM consultor_opinioes WHERE guid LIKE ?",
            ),
            ("aceite-190-%",),
        )
        colunas = (
            "guid",
            "ticker",
            "casa",
            "recomendacao",
            "preco_alvo",
            "resumo",
            "data_materia",
            "link",
        )
        gravadas = [dict(zip(colunas, linha)) for linha in cur.fetchall()]
    finally:
        conn.close()
    assert len(gravadas) == 3
    fechamentos = armazenamento.get_fechamentos(["PETR4"])
    linhas = agrupar_por_ativo(gravadas, referencia=referencia, fechamentos=fechamentos)

    html = _pagina(monkeypatch, linhas, gravadas)
    assert "atingido em 16/11 · R$ 45,20" in html
    assert "faltam +13,4% · fech. 19/11" in html
    assert "faltam -4,8% · fech. 19/11" in html
    assert "Até o alvo</th>" in html
    assert html.count(LINHA_METODO) == 1
    assert 'title="Alvo R$ 45,00 · antes da matéria: R$ 40,00 em 10/11 (alta)"' in html


def test_sem_opinioes_sem_linha_de_metodo(monkeypatch):
    html = _pagina(monkeypatch, [], [])
    assert "Até o alvo: compara" not in html
