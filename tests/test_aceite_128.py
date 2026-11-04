import os
import time
import subprocess
import sys
import pytest
from app.banco import DBInacessivelError


def test_fast_import(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@127.0.0.1:1/x")
    start = time.time()
    subprocess.run(
        [sys.executable, "-c", "import app.main"], env=os.environ, check=True
    )
    assert time.time() - start < 3.0


@pytest.fixture
def clean_db():
    if os.path.exists("data.db"):
        os.remove("data.db")
    yield
    if os.path.exists("data.db"):
        os.remove("data.db")


def test_healthz_and_root_no_sqlite(monkeypatch, clean_db):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@127.0.0.1:1/x")
    import app.banco

    # Ensure fresh state
    app.banco._backend_checked = False
    app.banco._backend_cached = None
    app.banco._disjuntor_aberto_ate = None
    app.banco._disjuntor_aberto_desde = None
    if os.path.exists("data.db"):
        os.remove("data.db")

    from app.main import app
    from fastapi.testclient import TestClient

    client = TestClient(app)

    res = client.get("/healthz")
    assert res.status_code == 200
    res = client.get("/")
    assert res.status_code == 200

    assert not os.path.exists("data.db")


def test_circuit_breaker(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@127.0.0.1:1/x")
    import app.banco

    app.banco._backend_checked = False
    app.banco._backend_cached = None
    app.banco._disjuntor_aberto_ate = None
    app.banco._disjuntor_aberto_desde = None
    app.banco._pool = None

    import psycopg_pool

    # Manually spy and patch without mocker
    original_getconn = psycopg_pool.ConnectionPool.getconn
    call_count = [0]

    def mock_getconn(self, *args, **kwargs):
        call_count[0] += 1
        raise Exception("mocked fail")

    psycopg_pool.ConnectionPool.getconn = mock_getconn

    # Needs to open pool to fail inside getconn
    def mock_init(self, *args, **kwargs):
        pass

    original_init = psycopg_pool.ConnectionPool.__init__
    psycopg_pool.ConnectionPool.__init__ = mock_init

    try:
        app.banco.get_connection()
    except DBInacessivelError:
        pass

    assert call_count[0] == 1

    try:
        app.banco.get_connection()
    except DBInacessivelError:
        pass

    assert call_count[0] == 1  # Circuit breaker is open

    original_time = time.time
    app.banco.time.time = lambda: original_time() + 31
    try:
        app.banco.get_connection()
    except DBInacessivelError:
        pass

    assert call_count[0] == 2

    # Restore
    psycopg_pool.ConnectionPool.getconn = original_getconn
    psycopg_pool.ConnectionPool.__init__ = original_init
    app.banco.time.time = original_time


def test_api_sistema(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@127.0.0.1:1/x")
    from app.services.sistema import verificar_banco, PROBLEMA
    import app.banco

    app.banco._backend_checked = False
    app.banco._backend_cached = None
    app.banco._disjuntor_aberto_ate = None
    app.banco._disjuntor_aberto_desde = None
    app.banco._pool = None

    try:
        app.banco.get_connection()
    except Exception:
        pass

    info = app.banco.diagnostico()
    item = verificar_banco(info)
    assert item.nivel == PROBLEMA
    assert "Postgres configurado e inacessível desde" in item.resumo
