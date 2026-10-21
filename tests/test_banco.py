import pytest
from datetime import date
from unittest.mock import MagicMock
from app.banco import (
    gravar_snapshot,
    ler_snapshot,
    listar_datas,
    get_backend_type,
    init_db,
)


@pytest.fixture(autouse=True)
def reset_db_initialized():
    import app.banco

    app.banco._db_initialized = False
    app.banco._backend_checked = False
    app.banco._backend_cached = None
    app.banco.init_db()


def test_fallback_sqlite(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("RENDER", raising=False)
    assert get_backend_type() == "sqlite_efemero"


def test_upsert_sqlite(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    init_db()
    payload1 = {"valor": 1}
    gravar_snapshot("painel1", date(2023, 10, 1), "ok", "fonte1", payload1)
    lido = ler_snapshot("painel1", date(2023, 10, 1))
    assert lido == payload1
    payload2 = {"valor": 2}
    gravar_snapshot("painel1", date(2023, 10, 1), "ok", "fonte2", payload2)
    lido2 = ler_snapshot("painel1", date(2023, 10, 1))
    assert lido2 == payload2


def test_listar_datas(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    init_db()
    gravar_snapshot("painel2", date(2023, 10, 1), "ok", "f1", {})
    gravar_snapshot("painel2", date(2023, 10, 2), "ok", "f1", {})
    datas = listar_datas("painel2")
    assert datas == ["2023-10-02", "2023-10-01"]


def test_sql_generation_postgres(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgres://mock")
    import app.banco as banco

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    def mock_get_connection():
        return mock_conn, "postgres"

    monkeypatch.setattr(banco, "get_connection", mock_get_connection)
    monkeypatch.setattr(banco, "init_db", lambda: None)

    gravar_snapshot("p", date(2023, 1, 1), "e", "f", {"a": 1})

    call_args = mock_cursor.execute.call_args
    assert call_args is not None
    query, params = call_args[0]

    assert "INSERT INTO snapshots_paineis" in query
    assert "ON CONFLICT (painel, data_referencia)" in query
    assert "DO UPDATE SET estado = EXCLUDED.estado" in query

    assert params[0] == "p"
    assert params[1] == date(2023, 1, 1)
    assert params[2] == "e"
    assert params[3] == "f"
    assert params[4] == '{"a": 1}'
