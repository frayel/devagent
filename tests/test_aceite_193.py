"""Aceite da spec 193: o Consultor de um pregão passado sai de uma função só.

Sem rede, no SQLite de teste: o arranjo da spec 131 (recomendações `Comprar`
em 01/11/2023 e 10 pregões de fechamento), a página e o JSON contra a função
`consultor_de_pregao_passado`.
"""

from __future__ import annotations

import inspect
import json
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from devagent.aceite import exigir_spec_done

SENHA = "senha_secreta"
D = "2023-11-01"
MENSAGEM = "+5.0% contra o IBOV em 5 pregões"
# Como `salvar_recomendacoes` grava: o JSON do consenso das casas. Vazio, o
# `StrictUndefined` dos testes reprovaria `item.consenso.consenso` no template.
CONSENSO = json.dumps({"consenso": "sem cobertura", "preco_alvo_mediano": None})


def _arranjo(monkeypatch, n_recomendacoes: int, com_ibov_futuro: bool = True):
    """`n` recomendações `Comprar` em 01/11/2023 e 10 pregões (01 a 10/11):
    o ativo fecha 10·(1+0,02·i) e o `^BVSP` 100·(1+0,01·i) no pregão i."""
    import app.main
    from app.consultor.armazenamento import get_connection, init_db

    init_db()
    conn, _ = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM consultor_recomendacoes")
    c.execute("DELETE FROM consultor_fechamentos")
    tickers = [f"TICK{i}" for i in range(1, n_recomendacoes + 1)]
    for ticker in tickers:
        c.execute(
            "INSERT INTO consultor_recomendacoes (timestamp, ticker, decisao_final, "
            "regra_tecnica, consenso, preco, gatilho) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("2023-11-01 18:00:00 BRT", ticker, "Comprar", "R1", CONSENSO, 10.0, "-"),
        )
    datas = []
    for i in range(10):
        dp = (datetime(2023, 11, 1) + timedelta(days=i)).strftime("%Y-%m-%d")
        datas.append(dp)
        if com_ibov_futuro or i != 5:
            c.execute(
                "INSERT INTO consultor_fechamentos (data_pregao, ticker, preco_fechamento) "
                "VALUES (?, ?, ?)",
                (dp, "^BVSP", 100.0 * (1 + i * 0.01)),
            )
        for ticker in tickers:
            c.execute(
                "INSERT INTO consultor_fechamentos (data_pregao, ticker, preco_fechamento) "
                "VALUES (?, ?, ?)",
                (dp, ticker, 10.0 * (1 + i * 0.02)),
            )
    conn.commit()
    conn.close()

    monkeypatch.setenv("CONSULTOR_SENHA", SENHA)
    monkeypatch.setattr(app.main, "obter_pregoes_disponiveis", lambda a, b, c: datas)
    return datas


def _espiar(monkeypatch) -> dict[str, int]:
    """Conta as conexões do Consultor e as consultas a `consultor_fechamentos`."""
    from app.consultor import armazenamento

    original = armazenamento.get_connection
    contagem = {"conexoes": 0, "fechamentos": 0}

    def _rastrear(sql: str) -> None:
        if "consultor_fechamentos" in sql and sql.lstrip().upper().startswith("SELECT"):
            contagem["fechamentos"] += 1

    def espiao():
        contagem["conexoes"] += 1
        conn, backend = original()
        conn.set_trace_callback(_rastrear)
        return conn, backend

    monkeypatch.setattr(armazenamento, "get_connection", espiao)
    return contagem


def _cliente() -> TestClient:
    from app.main import app

    return TestClient(app)


def test_pagina_historica_com_poucas_conexoes(monkeypatch):
    exigir_spec_done("193")
    _arranjo(monkeypatch, 80)
    contagem = _espiar(monkeypatch)

    res = _cliente().get(f"/consultor?data={D}", auth=("consultor", SENHA))

    assert res.status_code == 200
    assert MENSAGEM in res.text
    assert contagem["conexoes"] <= 8, contagem


def test_laco_nao_consulta_o_banco(monkeypatch):
    exigir_spec_done("193")
    consultas = []
    for n in (1, 80):
        _arranjo(monkeypatch, n)
        contagem = _espiar(monkeypatch)
        res = _cliente().get(f"/consultor?data={D}", auth=("consultor", SENHA))
        assert res.status_code == 200
        consultas.append(contagem["fechamentos"])
    assert consultas[0] == consultas[1], consultas
    assert consultas[1] <= 6, consultas


def test_funcao_entrega_placar_e_decisao_tecnica(monkeypatch):
    exigir_spec_done("193")
    from app.consultor.placar import consultor_de_pregao_passado

    _arranjo(monkeypatch, 80)
    dados = consultor_de_pregao_passado(D, None)
    compras = dados["resultados"]["Comprar"]
    assert len(compras) == 80
    for item in compras:
        assert item["mensagem_confianca"] == MENSAGEM
        assert item["decisao_tecnica"] == "Comprar"
    assert set(dados["resultados"]) >= {
        "Comprar",
        "Vender",
        "Aguardar",
        "No radar",
        "Sem sinal",
    }
    assert dados["ativos_avaliados"] == 80
    assert dados["regras_confianca"] == {}
    assert dados["opinioes_status"] == {}


@pytest.mark.parametrize(
    "dia, esperado",
    [
        ("2023-11-09", "+17.1% contra o IBOV em 1 pregões"),
        ("2023-11-10", "ainda sem resultado"),
    ],
)
def test_borda_da_janela(monkeypatch, dia, esperado):
    exigir_spec_done("193")
    from app.consultor.armazenamento import get_connection
    from app.consultor.placar import consultor_de_pregao_passado

    _arranjo(monkeypatch, 1)
    conn, _ = get_connection()
    conn.execute(
        "UPDATE consultor_recomendacoes SET timestamp = ?",
        (f"{dia} 18:00:00 BRT",),
    )
    conn.commit()
    conn.close()

    item = consultor_de_pregao_passado(dia, None)["resultados"]["Comprar"][0]
    assert item["mensagem_confianca"] == esperado


def test_sem_ibov_no_pregao_futuro(monkeypatch):
    exigir_spec_done("193")
    from app.consultor.placar import consultor_de_pregao_passado

    _arranjo(monkeypatch, 3, com_ibov_futuro=False)
    for item in consultor_de_pregao_passado(D, None)["resultados"]["Comprar"]:
        assert item["mensagem_confianca"] == "ainda sem resultado"


def test_json_igual_a_funcao(monkeypatch):
    exigir_spec_done("193")
    import app.main
    from app.consultor import consenso_yahoo
    from app.consultor.placar import consultor_de_pregao_passado

    _arranjo(monkeypatch, 80)
    monkeypatch.setattr(consenso_yahoo, "anexar", lambda *a, **k: None)

    res = _cliente().get(f"/api/consultor?data={D}", auth=("consultor", SENHA))
    assert res.status_code == 200
    corpo = res.json()
    resultados_json = corpo.get("consultor", corpo).get("resultados", {})

    esperado = consultor_de_pregao_passado(D, app.main._referencia_do_dia(D))
    assert resultados_json == esperado["resultados"]


def test_rotas_nao_montam_o_historico():
    exigir_spec_done("193")
    import app.main

    for rota in (app.main.pagina_consultor, app.main.api_consultor):
        fonte = inspect.getsource(rota)
        assert "consultor_fechamentos" not in fonte, rota.__name__
        assert "_calcular_excesso" not in fonte, rota.__name__
        assert "consultor_de_pregao_passado" in fonte, rota.__name__
