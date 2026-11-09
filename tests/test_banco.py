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


def test_diagnostico_cache_bypass(monkeypatch):
    import time
    from app.banco import diagnostico, DBInacessivelError
    import app.banco

    monkeypatch.setattr(
        app.banco, "_diagnostico_cache", {"tipo": "Postgres", "tamanho": "10 MB"}
    )
    monkeypatch.setattr(app.banco, "_diagnostico_cache_time", time.time())
    monkeypatch.setattr(app.banco, "_disjuntor_aberto_desde", "10:00")

    def mock_get_connection():
        raise DBInacessivelError("Disjuntor aberto")

    monkeypatch.setattr(app.banco, "get_connection", mock_get_connection)

    result = diagnostico()
    assert "erro" in result
    assert result["erro"] == "Postgres configurado e inacessível desde 10:00"


def test_abrir_pool_reseta_disjuntor(monkeypatch):
    """Regressão #793: abrir_pool deve resetar o disjuntor para que o app não acorde travado."""
    import app.banco as banco

    banco._disjuntor_aberto_ate = 9999999999.0
    banco._disjuntor_aberto_desde = "10:00"

    mock_pool = MagicMock()
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@mock/db")
    monkeypatch.setattr(banco, "get_backend_type", lambda: "postgres")
    monkeypatch.setattr(banco, "_obter_pool", lambda db_url: mock_pool)

    banco.abrir_pool()

    assert mock_pool.open.called
    assert banco._disjuntor_aberto_ate is None
    assert banco._disjuntor_aberto_desde is None


def test_pool_timeout_nao_abre_disjuntor(monkeypatch):
    """Regressão #793: PoolTimeout é contenção interna temporária do pool e não deve

    abrir o disjuntor de 30s para o banco inteiro.
    """
    import app.banco as banco
    from psycopg_pool import PoolTimeout

    banco._disjuntor_aberto_ate = None
    banco._disjuntor_aberto_desde = None

    mock_pool = MagicMock()
    mock_pool.closed = False
    mock_pool.getconn.side_effect = PoolTimeout("pool exhausted")

    with pytest.raises(banco.DBInacessivelError):
        banco._ConexaoDoPool(mock_pool)

    # Disjuntor NÃO deve ter sido aberto para PoolTimeout
    assert banco._disjuntor_aberto_ate is None
    assert banco._disjuntor_aberto_desde is None


def test_conexao_do_pool_auto_abre_se_pool_fechado(monkeypatch):
    """Regressão #793: _ConexaoDoPool deve chamar pool.open() se o pool estiver fechado

    em vez de travar o disjuntor imediatamente.
    """
    import app.banco as banco

    mock_conn = MagicMock()
    mock_pool = MagicMock()
    mock_pool.closed = True

    def mock_open(wait=True):
        mock_pool.closed = False

    mock_pool.open.side_effect = mock_open
    mock_pool.getconn.return_value = mock_conn

    conn = banco._ConexaoDoPool(mock_pool)
    assert mock_pool.open.called
    assert conn._conn is mock_conn
