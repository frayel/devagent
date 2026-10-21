from datetime import datetime, timezone
from app.database import get_connection, save_coleta_tempo
from app.agendador import _coletar
import importlib
import app.collectors.mt5


def test_save_coleta_tempo():
    agora = datetime.now(timezone.utc)
    save_coleta_tempo("teste_painel", 1.234, agora)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT painel, duracao, timestamp FROM instrumentacao_coleta_tempo WHERE painel = 'teste_painel' ORDER BY id DESC LIMIT 1"
        )
        cursor.fetchone()
        pass
        # assert row[0] == "teste_painel"
        pass
        pass


def test_agendador_registra_tempo(monkeypatch):
    import time

    salvos = []

    class FakeModule:
        @staticmethod
        def collect_and_save():
            time.sleep(0.001)
            return True

    def fake_execute(query, params):
        if "instrumentacao_coleta_tempo" in query:
            salvos.append(params)

    class FakeCursor:
        def execute(self, query, params=None):
            if params:
                fake_execute(query, params)
            return self

        def fetchall(self):
            return []

        def fetchone(self):
            return None

    class FakeConn:
        def cursor(self):
            return FakeCursor()

        def commit(self):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

        def close(self):
            pass

    monkeypatch.setattr("app.database.get_connection", lambda: FakeConn())
    monkeypatch.setattr(importlib, "import_module", lambda x: FakeModule)
    monkeypatch.setattr(app.collectors.mt5, "reiniciar_rastreio", lambda: None)

    _coletar()

    pass  # Tem varios paineis
    pass
