"""Aceite da spec 179: a série diária é gravada em lote.

Sem rede e só em `tmp_path` (o SQLite do fixture `setup_db` do conftest).
"""

from __future__ import annotations

import json
from datetime import date

import pytest

import app.banco
from devagent.aceite import exigir_spec_done


@pytest.fixture(autouse=True)
def _spec_done():
    exigir_spec_done("179")


BARRAS = [
    {"data": "2026-11-16", "close": 38.10},
    {"data": "2026-11-17", "close": 38.42},
    {"data": "2026-11-17", "close": 38.50},
]


class _CursorFalso:
    def __init__(self, registro: list) -> None:
        self.registro = registro

    def execute(self, sql, params=None):
        self.registro.append(("execute", sql, params))

    def executemany(self, sql, params):
        self.registro.append(("executemany", sql, list(params)))

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _ConexaoFalsa:
    def __init__(self) -> None:
        self.registro: list = []
        self.commits = 0
        self.fechada = False

    def cursor(self):
        return _CursorFalso(self.registro)

    def commit(self):
        self.commits += 1

    def close(self):
        self.fechada = True


@pytest.mark.parametrize("backend", ["postgres", "sqlite_efemero"])
def test_uma_chamada_por_serie(monkeypatch, backend):
    conn = _ConexaoFalsa()
    monkeypatch.setattr(app.banco, "init_db", lambda: None)
    monkeypatch.setattr(app.banco, "get_connection", lambda: (conn, backend))

    app.banco.gravar_serie("PETR4", BARRAS)

    lotes = [r for r in conn.registro if r[0] == "executemany"]
    inserts = [r for r in conn.registro if r[0] == "execute" and "INSERT" in r[1]]
    assert len(lotes) == 1
    assert inserts == []
    assert conn.commits == 1
    assert conn.fechada

    tuplas = lotes[0][2]
    assert [t[:3] for t in tuplas] == [
        ("PETR4", "2026-11-16", '[{"data": "2026-11-16", "close": 38.1}]'),
        ("PETR4", "2026-11-17", '[{"data": "2026-11-17", "close": 38.42}]'),
        ("PETR4", "2026-11-17", '[{"data": "2026-11-17", "close": 38.5}]'),
    ]
    assert len({t[3] for t in tuplas}) == 1
    assert [json.loads(t[2]) for t in tuplas] == [[b] for b in BARRAS]


def test_mesmo_conteudo_no_banco():
    _, backend = app.banco.get_connection()
    assert backend == "sqlite_efemero"

    app.banco.gravar_serie("PETR4", BARRAS)

    conn, _ = app.banco.get_connection()
    try:
        linhas = conn.execute(
            "SELECT COUNT(*) FROM series_diarias WHERE ticker = ?", ("PETR4",)
        ).fetchone()[0]
    finally:
        conn.close()
    assert linhas == 2

    serie = app.banco.ler_serie("PETR4", date(2026, 11, 16), date(2026, 11, 17))
    assert [b["close"] for b in serie] == [38.1, 38.5]


def test_lista_vazia_nao_abre_conexao(monkeypatch):
    def _proibido():
        raise AssertionError("gravar_serie([]) não deveria abrir conexão")

    monkeypatch.setattr(app.banco, "get_connection", _proibido)
    assert app.banco.gravar_serie("PETR4", []) is None
