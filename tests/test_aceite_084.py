from datetime import datetime, timezone
from app.banco import init_db as banco_init_db
from app.consultor.armazenamento import init_db as consultor_init_db
from app.services.consultor_opinioes import (
    get_llm_uso_hoje,
    incrementar_llm_uso,
    extrair_opinioes,
)
from app.consultor.armazenamento import get_opinioes_status


def test_postgres_tabelas_criadas(monkeypatch):
    comandos = []

    class FakeCursor:
        def execute(self, query, params=None):
            comandos.append(query)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    class FakeConn:
        def cursor(self):
            return FakeCursor()

        def commit(self):
            pass

        def close(self):
            pass

    def fake_get_connection():
        return FakeConn(), "postgres"

    monkeypatch.setattr(
        "app.consultor.armazenamento.get_connection", fake_get_connection
    )

    consultor_init_db()

    achou_tabela = any(
        "CREATE TABLE IF NOT EXISTS consultor_llm_uso" in cmd for cmd in comandos
    )
    achou_coluna = any(
        "processada INTEGER NOT NULL DEFAULT 0" in cmd for cmd in comandos
    )
    achou_alter = any(
        "ALTER TABLE consultor_fila_materias ADD COLUMN IF NOT EXISTS processada" in cmd
        for cmd in comandos
    )

    assert achou_tabela, "Faltou a tabela consultor_llm_uso"
    assert achou_coluna, "Faltou a coluna processada no CREATE TABLE"
    assert achou_alter, "Faltou o ALTER TABLE"


def test_sqlite_fluxo_completo(monkeypatch):
    banco_init_db()
    consultor_init_db()

    # Check extrair_opinioes without GEMINI_API_KEY
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    extrair_opinioes()
    status = get_opinioes_status()
    assert status["status"] == "sem_chave"


def test_fuso_horario(monkeypatch):
    class MockDatetime:
        @classmethod
        def now(cls, tz=None):
            # Simulate 23:30 UTC -> 20:30 BRT
            return datetime(2026, 10, 24, 23, 30, tzinfo=timezone.utc)

    monkeypatch.setattr("app.services.consultor_opinioes.datetime", MockDatetime)

    banco_init_db()
    consultor_init_db()

    # Check if get_llm_uso_hoje uses BRT
    incrementar_llm_uso()
    assert get_llm_uso_hoje() == 1
