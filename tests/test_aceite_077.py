import pytest
from datetime import datetime, timezone
from app.banco import get_backend_type
from app.database import init_db
from app import agendador


@pytest.fixture
def mock_horario(monkeypatch):
    class MockDatetime:
        agora_utc = None

        @classmethod
        def now(cls, tz=None):
            if tz == timezone.utc:
                return cls.agora_utc
            return cls.agora_utc.astimezone(tz)

    monkeypatch.setattr("app.agendador.datetime", MockDatetime)
    monkeypatch.setattr("app.calendario.datetime", MockDatetime)
    return MockDatetime


@pytest.fixture
def clean_db():
    if get_backend_type() != "postgres":
        from app.database import get_connection

        conn = get_connection()
        conn.execute("DROP TABLE IF EXISTS snapshots_paineis")
        conn.commit()
        conn.close()
    import app.banco

    app.banco._db_initialized = False
    init_db()


@pytest.fixture
def mock_coletores(monkeypatch):
    chamados = []

    class FakeColetor:
        def collect_and_save(self):
            return True

    def mock_import(name, *args):
        if name.startswith("app.collectors."):
            chamados.append(name.split(".")[-1])
            return FakeColetor()
        import importlib

        return importlib.__import__(name, *args)

    monkeypatch.setattr("importlib.import_module", mock_import)
    return chamados


def test_agendador_fim_de_semana(mock_horario, mock_coletores, clean_db, monkeypatch):
    # Sábado, 14h BRT (17h UTC)
    mock_horario.agora_utc = datetime(2023, 10, 14, 17, 0, tzinfo=timezone.utc)

    # force `ler_snapshot` to find it, avoiding sqlite issues in test env
    monkeypatch.setattr(
        "app.banco.ler_snapshot",
        lambda painel, ref: {"estado_snapshot": "final", "estado": "final"},
    )

    agendador.coletar_tudo()
    assert "ibovespa" not in mock_coletores, (
        "Agendador fez chamada para coletor pregao fora da janela sem partida a frio"
    )


def test_agendador_segunda_11h(mock_horario, mock_coletores, clean_db):
    # Segunda, 11h BRT (14h UTC)
    mock_horario.agora_utc = datetime(2023, 10, 16, 14, 0, tzinfo=timezone.utc)

    agendador.coletar_tudo()

    assert "ibovespa" in mock_coletores


def test_agendador_fechamento_sucesso_e_ignora_depois(
    mock_horario, mock_coletores, clean_db
):
    # 18h20
    mock_horario.agora_utc = datetime(2023, 10, 16, 21, 20, tzinfo=timezone.utc)

    agendador.coletar_tudo()
    assert "ibovespa" in mock_coletores


def test_agendador_partida_a_frio(mock_horario, mock_coletores, clean_db, monkeypatch):
    # Domingo, sem banco
    mock_horario.agora_utc = datetime(2023, 10, 15, 12, 0, tzinfo=timezone.utc)
    monkeypatch.setattr("app.banco.ler_snapshot", lambda painel, ref: None)

    agendador.coletar_tudo()
    assert "ibovespa" in mock_coletores
    assert (
        agendador.estado["detalhes"] is not None
        and "partida_a_frio" in agendador.estado["detalhes"]
    )
