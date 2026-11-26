"""Aceite da spec 198: o diagnóstico de opiniões do Consultor sai de uma função só.

Sem rede. Para separar os dois bancos, o `get_connection` que
`app.consultor.armazenamento` importa de `app.banco` (o único importador fora
de `app/banco.py`) abre um segundo SQLite em `tmp_path`, como o Postgres de
produção. O `app.banco.get_connection` em si fica como está, porque os painéis
lidos pela página também passam por ele; o `app.database.get_connection` segue
no SQLite de teste, com a fila vazia.
"""

from __future__ import annotations

import inspect
import sqlite3
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from devagent.aceite import exigir_spec_done

SENHA = "senha_secreta"
RAIZ = Path(__file__).resolve().parent.parent
D = "2023-11-01"
OITO = {
    "codigo",
    "motivo",
    "desde",
    "ultima_extracao_em",
    "materias_processadas",
    "opinioes_gravadas",
    "descartadas",
    "fila_pendentes",
}


@pytest.fixture(autouse=True)
def _spec_done():
    exigir_spec_done("198")


@pytest.fixture
def banco_consultor(monkeypatch, tmp_path):
    """O banco do Consultor num arquivo à parte, com o arranjo do exemplo."""
    from app.consultor import armazenamento

    caminho = tmp_path / "consultor.db"

    def abrir():
        return sqlite3.connect(str(caminho)), "sqlite_efemero"

    monkeypatch.setattr(armazenamento, "get_connection", abrir)
    monkeypatch.setattr(armazenamento, "_consultor_db_initialized", False)
    armazenamento.init_db()

    conn, _ = abrir()
    c = conn.cursor()
    c.execute("DELETE FROM consultor_fila_materias")
    c.execute("DELETE FROM consultor_opinioes")
    c.execute("DELETE FROM consultor_opinioes_status")
    for i in range(10):
        c.execute(
            "INSERT INTO consultor_fila_materias (guid, titulo, descricao, conteudo, "
            "data_publicacao, link, tickers_citados, criado_em, processada) "
            "VALUES (?, ?, '', '', ?, '', '[]', ?, ?)",
            (
                f"g{i}",
                f"Matéria {i}",
                "2026-11-25T12:00:00+00:00",
                "2026-11-25T12:00:00+00:00",
                0 if i < 7 else 1,
            ),
        )
    c.execute(
        "INSERT INTO consultor_opinioes_status (status, motivo, desde, "
        "ultima_extracao_em, materias_processadas, opinioes_gravadas, descartadas) "
        "VALUES ('ok', '', '2026-11-25T14:00:00Z', '2026-11-25T14:00:00Z', 3, 0, 0)"
    )
    conn.commit()
    conn.close()

    from app.database import get_connection as sqlite_local

    local = sqlite_local()
    try:
        assert (
            local.execute("SELECT COUNT(*) FROM consultor_fila_materias").fetchone()[0]
            == 0
        )
    finally:
        local.close()

    monkeypatch.setenv("CONSULTOR_SENHA", SENHA)
    import app.consultor.calculador as calc

    monkeypatch.setattr(calc, "_consultor_cache", None)
    return caminho


def _cliente() -> TestClient:
    from app.main import app

    return TestClient(app)


def _status(**campos) -> dict:
    base = {
        "status": "ok",
        "motivo": "",
        "desde": "2026-11-25T14:00:00Z",
        "ultima_extracao_em": "2026-11-25T14:00:00Z",
        "materias_processadas": 3,
        "opinioes_gravadas": 0,
        "descartadas": 0,
    }
    base.update(campos)
    return base


def test_contar_fila_pendente_no_banco_do_consultor(banco_consultor):
    from app.consultor.armazenamento import contar_fila_pendente

    assert contar_fila_pendente() == 7


def test_pagina_e_json_mostram_a_fila(banco_consultor):
    cliente = _cliente()
    res = cliente.get("/consultor", auth=("consultor", SENHA))
    assert res.status_code == 200
    assert "7 matérias na fila, a próxima extração é na próxima rodada." in res.text

    res = cliente.get("/api/consultor", auth=("consultor", SENHA))
    assert res.status_code == 200
    fontes = res.json()["fontes_opiniao"]
    assert fontes["fila"] == 7
    assert fontes["diagnostico"]["codigo"] == "fila"
    assert fontes["diagnostico"]["fila_pendentes"] == 7


@pytest.mark.parametrize(
    "status, fila, opinioes, esperado",
    [
        (_status(status="sem_chave"), 0, [], "sem_chave"),
        (_status(status="cota"), 0, [], "cota"),
        (_status(status="erro", motivo="falhou"), 0, [], "erro"),
        (_status(status="invalido"), 0, [], "erro"),
        (_status(ultima_extracao_em=""), 0, [], "aguardando"),
        (_status(), 5, [], "fila"),
        (_status(descartadas=2), 0, [], "descartadas"),
        (_status(), 0, [], "sem_materias"),
        (_status(), 0, [{"ticker": "PETR4"}], "ok"),
    ],
)
def test_arvore_de_hoje(monkeypatch, status, fila, opinioes, esperado):
    from app.consultor import armazenamento
    from app.consultor.diagnostico import diagnostico_de_opinioes

    monkeypatch.setattr(armazenamento, "contar_fila_pendente", lambda: fila)
    diag = diagnostico_de_opinioes(
        {"opinioes_status": status, "opinioes_recentes": opinioes}, False
    )
    assert diag["codigo"] == esperado
    assert set(diag) == OITO
    assert diag["fila_pendentes"] == fila


def test_pregao_passado_nao_consulta_a_fila(monkeypatch):
    from app.consultor import armazenamento
    from app.consultor.diagnostico import diagnostico_de_opinioes

    def explode():
        raise AssertionError("não devia contar a fila")

    monkeypatch.setattr(armazenamento, "contar_fila_pendente", explode)
    diag = diagnostico_de_opinioes(
        {"opinioes_status": {}, "opinioes_recentes": []}, True
    )
    assert diag["codigo"] == "pregao_passado"
    assert diag["fila_pendentes"] is None
    assert set(diag) == OITO


def test_erro_vira_codigo_erro(banco_consultor, monkeypatch):
    from app.consultor import armazenamento
    from app.consultor.diagnostico import diagnostico_de_opinioes

    def falha():
        raise RuntimeError("banco fora do ar")

    monkeypatch.setattr(armazenamento, "contar_fila_pendente", falha)
    diag = diagnostico_de_opinioes(
        {"opinioes_status": _status(), "opinioes_recentes": []}, False
    )
    assert diag["codigo"] == "erro"
    assert diag["motivo"] == "diagnóstico indisponível"
    assert set(diag) == OITO

    res = _cliente().get("/api/consultor", auth=("consultor", SENHA))
    assert res.status_code == 200
    fontes = res.json()["fontes_opiniao"]
    assert fontes["diagnostico"]["codigo"] == "erro"
    assert fontes["fila"] == fontes["diagnostico"]["fila_pendentes"]


def test_pregao_passado_na_pagina_e_no_json(banco_consultor, monkeypatch):
    import app.main

    monkeypatch.setattr(
        app.main, "obter_pregoes_disponiveis", lambda a, b, c: [D, "2023-11-02"]
    )
    cliente = _cliente()
    res = cliente.get(f"/consultor?data={D}", auth=("consultor", SENHA))
    assert res.status_code == 200
    assert "Nenhuma opinião gravada nos 30 dias até 01/11/2023." in res.text
    assert "Aguardando a primeira extração" not in res.text
    assert "Última extração: nunca" not in res.text

    res = cliente.get(f"/api/consultor?data={D}", auth=("consultor", SENHA))
    assert res.status_code == 200
    assert res.json()["fontes_opiniao"]["diagnostico"]["codigo"] == "pregao_passado"


def test_rotas_nao_contam_a_fila():
    import app.main

    for rota in (app.main.pagina_consultor, app.main.api_consultor):
        fonte = inspect.getsource(rota)
        assert "consultor_fila_materias" not in fonte
        assert "app.database import get_connection" not in fonte

    saida = subprocess.run(
        ["grep", "-rln", "from app.database import get_connection", "app"],
        cwd=RAIZ,
        capture_output=True,
        text=True,
    ).stdout.split()
    assert saida == ["app/banco.py"], saida
