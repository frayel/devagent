import time
from app import agendador


def test_backtest_unico(monkeypatch):
    # Resetar estado
    agendador._backtest_rodando = False
    agendador.estado["detalhes"] = None

    chamadas_backtest = []

    def mock_rodar_backtest():
        chamadas_backtest.append(1)
        time.sleep(0.5)

    monkeypatch.setattr(
        "app.consultor.avaliador_historico.rodar_backtest", mock_rodar_backtest
    )

    # Mocking importlib to just ignore dynamically imported modules
    # and only focus on consultor_historico being executed.
    # We must be careful to only intercept our own collectors and not standard library imports like datetime.

    original_import_module = __import__("importlib").import_module

    def mock_import_module(name):
        if name.startswith("app.collectors."):

            class DummyCollector:
                @staticmethod
                def collect_and_save():
                    return True

            return DummyCollector()
        return original_import_module(name)

    monkeypatch.setattr("importlib.import_module", mock_import_module)

    # It's easier to mock datetime in agendador to trigger consultor_historico
    import datetime

    class MockDatetime:
        @classmethod
        def now(cls, tz=None):
            # Return a saturday to trigger consultor_historico
            return datetime.datetime(2023, 1, 7, 12, 0, 0, tzinfo=datetime.timezone.utc)

    monkeypatch.setattr("app.agendador.datetime", MockDatetime)

    # Call the full pipeline via _coletar directly
    detalhes_manual = []
    agendador._coletar(estado_detalhes_manual=detalhes_manual)

    # It should be called once, not blocking, so we need to wait a bit
    time.sleep(0.1)
    assert len(chamadas_backtest) == 1

    # Check state that it's running
    assert agendador._backtest_rodando is True

    # Call again while the first one is still "running" (sleeping for 0.5s)
    agendador._coletar(estado_detalhes_manual=detalhes_manual)

    # Should not call rodar_backtest again
    assert len(chamadas_backtest) == 1

    # Should have recorded the message
    assert "consultor_historico: backtest anterior ainda em curso" in detalhes_manual

    # Wait for thread to finish
    time.sleep(0.5)

    # Ensure flag is reset
    assert agendador._backtest_rodando is False
