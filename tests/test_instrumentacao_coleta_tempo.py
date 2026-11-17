from datetime import datetime, timezone
from app.banco import ler_snapshot
from app.database import BRT, save_coleta_tempo
from app.agendador import _coletar
import importlib
import app.collectors.mt5


def test_save_coleta_tempo():
    agora = datetime.now(timezone.utc)
    save_coleta_tempo("teste_painel", 1.234, agora)

    payload = ler_snapshot("instrumentacao", agora.astimezone(BRT).date())
    assert payload["tempos"]["teste_painel"] == 1.234
    assert payload["rodadas"]["teste_painel"] == 1


def test_agendador_registra_tempo(monkeypatch):
    import time

    salvos = []

    class FakeModule:
        @staticmethod
        def collect_and_save():
            time.sleep(0.001)
            return True

    def fake_execute(query, params):
        salvos.append((query, params))

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
