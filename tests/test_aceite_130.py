import pytest
import asyncio
import time
from httpx import AsyncClient, ASGITransport
import ast
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def test_client():
    return TestClient(app)


def test_async_routes_have_await():
    with open("app/main.py", "r") as f:
        tree = ast.parse(f.read())

    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef):
            has_route = False
            for dec in node.decorator_list:
                if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute):
                    if dec.func.attr in ("get", "post", "put", "delete", "patch"):
                        has_route = True

            if has_route:
                has_await = any(isinstance(n, ast.Await) for n in ast.walk(node))
                assert has_await, f"Rota assíncrona {node.name} não contém await"


def test_snapshot_queries_count(test_client, monkeypatch):
    query_count = 0

    import app.banco

    original_cursor = app.banco.get_connection

    def get_connection_spy():
        conn, backend = original_cursor()

        class MockCursor:
            def __init__(self, c):
                self.c = c

            def execute(self, sql, *args, **kwargs):
                nonlocal query_count
                s = str(sql).lower()
                if hasattr(sql, "as_string"):
                    s = sql.as_string(conn).lower()
                elif isinstance(sql, bytes):
                    s = sql.decode("utf-8").lower()
                if "snapshots_paineis" in s:
                    query_count += 1
                return self.c.execute(sql, *args, **kwargs)

            def fetchone(self):
                return self.c.fetchone()

            def fetchall(self):
                return self.c.fetchall()

            def __enter__(self):
                self.c.__enter__()
                return self

            def __exit__(self, *args):
                return self.c.__exit__(*args)

        class MockConn:
            def cursor(self, *args, **kwargs):
                c = conn.cursor(*args, **kwargs)
                return MockCursor(c)

            def close(self):
                conn.close()

            def commit(self):
                conn.commit()

        return MockConn(), backend

    monkeypatch.setattr("app.banco.get_connection", get_connection_spy)

    def mock_listar_datas(*args, **kwargs):
        return ["2026-10-22"]

    monkeypatch.setattr("app.banco.listar_datas", mock_listar_datas)

    def mock_obter_pregoes(*args, **kwargs):
        return ["2026-10-22"]

    monkeypatch.setattr("app.main.obter_pregoes_disponiveis", mock_obter_pregoes)

    class DummyMercado:
        def mercado_aberto(self, dt):
            return False

        def pregao_corrente(self, dt):
            from datetime import date

            return date(2026, 10, 22)

        def ultimo_pregao_fechado(self, dt):
            from datetime import date

            return date(2026, 10, 22)

    monkeypatch.setattr("app.main.calendario", DummyMercado())

    import app.main

    original_get_seletor = app.main._get_seletor_context

    def mock_get_seletor(*args, **kwargs):
        ctx = original_get_seletor(*args, **kwargs)
        ctx["data_invalida"] = False
        return ctx

    monkeypatch.setattr("app.main._get_seletor_context", mock_get_seletor)

    resp = test_client.get("/")
    assert resp.status_code == 200
    assert query_count <= 3, (
        f"Foram feitas {query_count} consultas a snapshots_paineis, limite é 3"
    )


@pytest.mark.asyncio
async def test_healthz_latency_with_delayed_ler_snapshot(monkeypatch):
    import app.banco

    original_ler_snapshot = app.banco.ler_snapshot

    def delayed_ler_snapshot(*args, **kwargs):
        time.sleep(1)
        return original_ler_snapshot(*args, **kwargs)

    monkeypatch.setattr("app.banco.ler_snapshot", delayed_ler_snapshot)

    def mock_listar_datas(*args, **kwargs):
        return ["2026-10-22"]

    monkeypatch.setattr("app.banco.listar_datas", mock_listar_datas)

    def mock_obter_pregoes(*args, **kwargs):
        return ["2026-10-22"]

    monkeypatch.setattr("app.main.obter_pregoes_disponiveis", mock_obter_pregoes)

    class DummyMercado:
        def mercado_aberto(self, dt):
            return False

        def pregao_corrente(self, dt):
            from datetime import date

            return date(2026, 10, 22)

        def ultimo_pregao_fechado(self, dt):
            from datetime import date

            return date(2026, 10, 22)

    monkeypatch.setattr("app.main.calendario", DummyMercado())

    import app.main

    original_get_seletor = app.main._get_seletor_context

    def mock_get_seletor(*args, **kwargs):
        ctx = original_get_seletor(*args, **kwargs)
        ctx["data_invalida"] = False
        return ctx

    monkeypatch.setattr("app.main._get_seletor_context", mock_get_seletor)

    from app.main import app as main_app

    async with AsyncClient(
        transport=ASGITransport(app=main_app), base_url="http://test"
    ) as client:
        # Request index which will block the threadpool worker
        task_index = asyncio.create_task(client.get("/"))

        # Give it a small moment to start executing
        await asyncio.sleep(0.1)

        # Request healthz while index is running
        start_time = time.perf_counter()
        resp_healthz = await client.get("/healthz")
        elapsed = time.perf_counter() - start_time

        # Ensure healthz succeeds and responds fast
        assert resp_healthz.status_code == 200
        assert elapsed < 0.200, (
            f"/healthz demorou {elapsed:.3f}s (limite 200ms) enquanto / processava"
        )

        # Wait for index to finish so we don't leak tasks
        await task_index


def test_get_index_d1_criterio(test_client, monkeypatch):
    def mock_listar_datas(*args, **kwargs):
        return [
            "2026-10-22",
            "2026-10-21",
            "2026-10-20",
            "2026-10-19",
            "2026-10-16",
            "2026-10-15",
            "2026-10-14",
        ]

    monkeypatch.setattr("app.banco.listar_datas", mock_listar_datas)

    def mock_obter_pregoes(*args, **kwargs):
        return [
            "2026-10-22",
            "2026-10-21",
            "2026-10-20",
            "2026-10-19",
            "2026-10-16",
            "2026-10-15",
        ]

    monkeypatch.setattr("app.main.obter_pregoes_disponiveis", mock_obter_pregoes)

    class DummyMercado:
        def mercado_aberto(self, dt):
            return False

        def pregao_corrente(self, dt):
            from datetime import date

            return date(2026, 10, 22)

        def ultimo_pregao_fechado(self, dt):
            from datetime import date

            return date(2026, 10, 22)

    monkeypatch.setattr("app.main.calendario", DummyMercado())

    import app.main

    original_get_seletor = app.main._get_seletor_context

    def mock_get_seletor(*args, **kwargs):
        ctx = original_get_seletor(*args, **kwargs)
        ctx["data_invalida"] = False
        return ctx

    monkeypatch.setattr("app.main._get_seletor_context", mock_get_seletor)

    resp = test_client.get("/?data=D1")
    assert resp.status_code == 200
