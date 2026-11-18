from datetime import datetime, timezone
from app.banco import ler_snapshot
from app.database import BRT, save_coleta_tempo
from app.agendador import _coletar
import importlib


def test_save_coleta_tempo():
    agora = datetime.now(timezone.utc)
    save_coleta_tempo("teste_painel", 1.234, agora)

    payload = ler_snapshot("instrumentacao", agora.astimezone(BRT).date())
    assert payload["tempos"]["teste_painel"] == 1.234
    assert payload["rodadas"]["teste_painel"] == 1


def test_agendador_registra_tempo(monkeypatch):
    """Num pregão, cada coletor que rodou chega à instrumentação com tempo > 0."""
    import time

    from app import agendador
    import app.database
    from tests.test_aceite_154 import PREGAO, _relogio

    class FakeModule:
        @staticmethod
        def collect_and_save():
            time.sleep(0.001)
            return True

    rodaram = {"ibovespa", "mare"}

    def importar(nome):
        if nome.rsplit(".", 1)[-1] in rodaram:
            return FakeModule
        raise ImportError(f"coletor fora do teste: {nome}")

    recebidos: list[dict[str, float]] = []

    def espiar(tempos, vazias, timestamp, durante_pregao=False, **_):
        recebidos.append(dict(tempos))

    monkeypatch.setattr("app.collectors.mt5.reiniciar_rastreio", lambda: None)
    monkeypatch.setattr(importlib, "import_module", importar)
    monkeypatch.setattr(agendador, "datetime", _relogio(PREGAO))
    monkeypatch.setattr(agendador, "_avisar_falha", lambda *a, **k: None)
    monkeypatch.setattr(agendador, "_registrar_erro", lambda *a, **k: None)
    monkeypatch.setattr(app.database, "gravar_instrumentacao_rodada", espiar)

    _coletar()

    assert len(recebidos) == 1
    tempos = recebidos[0]
    assert set(tempos) == rodaram
    assert all(t > 0 for t in tempos.values())
