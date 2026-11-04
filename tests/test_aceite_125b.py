import pytest
from datetime import datetime, timezone, date
from app import agendador


@pytest.fixture
def mock_cenario(monkeypatch):

    # Prepara mock de banco
    snapshots = {}

    def mock_ler_snapshot(nome, ult_fechado):
        return snapshots.get((nome, ult_fechado))

    def mock_gravar_snapshot(nome, ult_fechado, estado, fonte, payload):
        snap = payload.copy()
        snap["estado_snapshot"] = estado
        snapshots[(nome, ult_fechado)] = snap

    monkeypatch.setattr("app.banco.ler_snapshot", mock_ler_snapshot)
    monkeypatch.setattr("app.banco.gravar_snapshot", mock_gravar_snapshot)

    # Evita que outros processos rodem
    for nome in (
        "highlights",
        "mare",
        "volume_alerts",
        "dolar_correlation",
        "sensibilidade_juros",
        "forca_relativa",
        "escudo_quedas",
        "coesao",
        "atrasadas_rally",
        "concentracao",
        "apetite_risco",
        "variacao_subita",
        "concentracao_setorial",
        "rotacao_capital",
        "faca_caindo",
        "compradores_fundo",
        "armadilha_abertura",
        "sobrevivencia_semanal",
        "radar_anomalia_fechamento",
        "volatilidade_silenciosa",
        "scanner_capitulacao",
        "radar_inflexao",
        "anomalia_peso",
        "radar_short_squeeze",
        "radar_congestionamento",
        "radar_liquidez_abertura",
        "esforco_resultado",
        "radar_divergencia_volume",
        "fator_peso_pesado",
        "falso_rompimento",
        "radar_absorcao_cruzada",
        "motores_indice",
        "clima_global",
        "relogio_volatilidade",
        "radar_anomalias_spread",
        "concentracao_ordens",
        "exaustao_tendencia",
        "exaustao_queda",
        "radar_exaustao_alta",
        "divergencia_ibov_dolar",
        "correlacao_di",
        "assimetria_risco_retorno",
        "consultor_historico",
        "consultor_opinioes",
        "consultor_fechamento",
    ):
        monkeypatch.setattr(f"app.collectors.{nome}.collect_and_save", lambda: True)

    def mock_listar_datas(nome):
        # mock list_datas just to show inclusion
        pass

    monkeypatch.setattr("app.banco.listar_datas", mock_listar_datas, raising=False)

    class CallTracker:
        def __init__(self):
            self.calls = 0

        def collect_and_save(self):
            self.calls += 1
            return True

    tracker = CallTracker()
    monkeypatch.setattr(
        "app.collectors.ibovespa.collect_and_save", tracker.collect_and_save
    )

    return snapshots, tracker


def test_marca_incompleto_20h05(monkeypatch, mock_cenario):
    snapshots, tracker = mock_cenario

    # 2026-11-02 é uma segunda-feira (pregao)
    agora = datetime(2026, 11, 2, 23, 5, tzinfo=timezone.utc)  # 20:05 BRT
    ult_fechado = date(2026, 11, 2)

    # Snapshot inicial
    snapshots[("ibovespa", ult_fechado)] = {
        "estado_snapshot": "ao_vivo",
        "fonte": "yfinance",
        "payload": "teste",
    }

    # Mocks
    monkeypatch.setattr("app.calendario.mercado_aberto", lambda dt: False)
    monkeypatch.setattr("app.calendario.pregao_corrente", lambda dt: ult_fechado)
    monkeypatch.setattr("app.calendario.ultimo_pregao_fechado", lambda dt: ult_fechado)
    monkeypatch.setattr("app.calendario.e_pregao", lambda d: True)

    # Fake datetime
    class FakeDatetime:
        @classmethod
        def now(cls, tz=None):
            return agora

    monkeypatch.setattr("app.agendador.datetime", FakeDatetime)

    agendador.coletar_tudo()

    # Check assertions
    snap = snapshots[("ibovespa", ult_fechado)]
    assert snap["estado_snapshot"] == "incompleto"
    assert snap["fonte"] == "yfinance"
    assert snap["payload"] == "teste"
    assert tracker.calls == 0
    assert "ibovespa: incompleto" in (agendador.estado.get("detalhes") or "")


def test_marca_incompleto_dia_seguinte(monkeypatch, mock_cenario):
    snapshots, tracker = mock_cenario

    # Dia seguinte: 2026-11-03 08:00 BRT (11:00 UTC)
    agora = datetime(2026, 11, 3, 11, 0, tzinfo=timezone.utc)
    ult_fechado = date(2026, 11, 2)  # o último pregão

    snapshots[("ibovespa", ult_fechado)] = {
        "estado_snapshot": "ao_vivo",
        "fonte": "yfinance",
        "payload": "teste",
    }

    monkeypatch.setattr("app.calendario.mercado_aberto", lambda dt: False)
    monkeypatch.setattr("app.calendario.pregao_corrente", lambda dt: date(2026, 11, 3))
    monkeypatch.setattr("app.calendario.ultimo_pregao_fechado", lambda dt: ult_fechado)
    monkeypatch.setattr("app.calendario.e_pregao", lambda d: True)

    class FakeDatetime:
        @classmethod
        def now(cls, tz=None):
            return agora

    monkeypatch.setattr("app.agendador.datetime", FakeDatetime)

    agendador.coletar_tudo()

    snap = snapshots[("ibovespa", ult_fechado)]
    assert snap["estado_snapshot"] == "incompleto"
    assert snap["fonte"] == "yfinance"
    assert tracker.calls == 0
    assert "ibovespa: incompleto" in (agendador.estado.get("detalhes") or "")


def test_nao_sobrescreve_final(monkeypatch, mock_cenario):
    snapshots, tracker = mock_cenario

    agora = datetime(2026, 11, 2, 23, 5, tzinfo=timezone.utc)  # 20:05 BRT
    ult_fechado = date(2026, 11, 2)

    snapshots[("ibovespa", ult_fechado)] = {
        "estado_snapshot": "final",
        "fonte": "yfinance",
    }

    monkeypatch.setattr("app.calendario.mercado_aberto", lambda dt: False)
    monkeypatch.setattr("app.calendario.pregao_corrente", lambda dt: ult_fechado)
    monkeypatch.setattr("app.calendario.ultimo_pregao_fechado", lambda dt: ult_fechado)
    monkeypatch.setattr("app.calendario.e_pregao", lambda d: True)

    class FakeDatetime:
        @classmethod
        def now(cls, tz=None):
            return agora

    monkeypatch.setattr("app.agendador.datetime", FakeDatetime)

    agendador.coletar_tudo()

    snap = snapshots[("ibovespa", ult_fechado)]
    assert snap["estado_snapshot"] == "final"
    assert tracker.calls == 0


def test_partida_a_frio_mantida(monkeypatch, mock_cenario):
    snapshots, tracker = mock_cenario

    agora = datetime(2026, 11, 2, 23, 5, tzinfo=timezone.utc)  # 20:05 BRT
    ult_fechado = date(2026, 11, 2)

    # sem snapshot

    monkeypatch.setattr("app.calendario.mercado_aberto", lambda dt: False)
    monkeypatch.setattr("app.calendario.pregao_corrente", lambda dt: ult_fechado)
    monkeypatch.setattr("app.calendario.ultimo_pregao_fechado", lambda dt: ult_fechado)
    monkeypatch.setattr("app.calendario.e_pregao", lambda d: True)

    class FakeDatetime:
        @classmethod
        def now(cls, tz=None):
            return agora

    monkeypatch.setattr("app.agendador.datetime", FakeDatetime)

    agendador.coletar_tudo()

    # Deve chamar collector
    assert tracker.calls == 1
