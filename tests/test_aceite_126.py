from datetime import datetime
from unittest.mock import MagicMock
from app.agendador import intervalo, _coletar
import app.agendador


def test_intervalo_feriado():
    # 02/11/2026 às 11h BRT - Feriado, deve devolver 2h (FORA_DO_PREGAO)
    agora_feriado = datetime.fromisoformat("2026-11-02T14:00:00+00:00")
    assert intervalo(agora_feriado) == app.agendador.FORA_DO_PREGAO


def test_intervalo_dia_util():
    # 28/10/2026 às 11h BRT - Dia útil, deve devolver 15min (NO_PREGAO)
    agora_util = datetime.fromisoformat("2026-10-28T14:00:00+00:00")
    assert intervalo(agora_util) == app.agendador.NO_PREGAO


def test_backtest_chamado_uma_vez_em_background(monkeypatch):
    from app.consultor import avaliador_historico
    import time

    mock_rodar = MagicMock()

    def slow_rodar():
        mock_rodar()
        time.sleep(0.5)

    monkeypatch.setattr(avaliador_historico, "rodar_backtest", slow_rodar)

    # Force _coletar to run consultor_historico by returning True for its condition
    class MockDatetime:
        @classmethod
        def now(cls, tz=None):
            # Saturday 2026-10-31
            return datetime.fromisoformat("2026-10-31T14:00:00+00:00")

    monkeypatch.setattr(app.agendador, "datetime", MockDatetime)

    # Mock other things to be fast/noop
    for nome in [
        "ibovespa",
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
        "consultor_opinioes",
        "consultor_fechamento",
    ]:
        monkeypatch.setattr(f"app.collectors.{nome}.collect_and_save", lambda: True)

    monkeypatch.setattr(
        "app.collectors.consultor_historico.collect_and_save", lambda: True
    )

    estado_detalhes_manual = []

    start = time.perf_counter()
    _coletar(estado_detalhes_manual)
    duration = time.perf_counter() - start

    # Ensure it didn't wait for slow_rodar
    assert duration < 0.4
    assert mock_rodar.call_count == 1

    # Try again while it's still running
    _coletar(estado_detalhes_manual)

    assert mock_rodar.call_count == 1
    assert any(
        "consultor_historico: backtest anterior ainda em curso" in d
        for d in estado_detalhes_manual
    )
