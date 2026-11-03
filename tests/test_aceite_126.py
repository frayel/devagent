import threading
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from app.agendador import intervalo, _coletar

def test_intervalo_feriado():
    BRT = ZoneInfo("America/Sao_Paulo")
    dt_feriado = datetime(2026, 11, 2, 11, 0, tzinfo=BRT).astimezone(timezone.utc)
    espera = intervalo(dt_feriado)
    assert espera.total_seconds() == 7200

def test_intervalo_normal():
    BRT = ZoneInfo("America/Sao_Paulo")
    dt_normal = datetime(2026, 10, 28, 11, 0, tzinfo=BRT).astimezone(timezone.utc)
    espera = intervalo(dt_normal)
    assert espera.total_seconds() == 900

def test_rodar_backtest_unico(monkeypatch):
    chamadas = 0

    def mock_rodar_backtest():
        nonlocal chamadas
        chamadas += 1

    monkeypatch.setattr("app.consultor.avaliador_historico.rodar_backtest", mock_rodar_backtest)
    import app.agendador
    app.agendador._backtest_thread = None

    for nome in ["ibovespa", "highlights", "mare", "volume_alerts", "dolar_correlation", "sensibilidade_juros", "forca_relativa", "escudo_quedas", "coesao", "atrasadas_rally", "concentracao", "apetite_risco", "variacao_subita", "concentracao_setorial", "rotacao_capital", "faca_caindo", "compradores_fundo", "armadilha_abertura", "sobrevivencia_semanal", "radar_anomalia_fechamento", "volatilidade_silenciosa", "scanner_capitulacao", "radar_inflexao", "anomalia_peso", "radar_short_squeeze", "radar_congestionamento", "radar_liquidez_abertura", "esforco_resultado", "radar_divergencia_volume", "fator_peso_pesado", "falso_rompimento", "radar_absorcao_cruzada", "motores_indice", "clima_global", "relogio_volatilidade", "radar_anomalias_spread", "concentracao_ordens", "exaustao_tendencia", "exaustao_queda", "radar_exaustao_alta", "divergencia_ibov_dolar", "correlacao_di", "assimetria_risco_retorno", "consultor_historico", "consultor_opinioes", "consultor_fechamento"]:
        monkeypatch.setattr(f"app.collectors.{nome}.collect_and_save", lambda: True)

    monkeypatch.setattr("datetime.datetime", type("MockDateTime", (), {"now": lambda tz: datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc)}))

    estado_detalhes_manual = []
    _coletar(estado_detalhes_manual)

    if app.agendador._backtest_thread is not None:
        app.agendador._backtest_thread.join()

    assert chamadas == 1

def test_rodar_backtest_simultaneo(monkeypatch):
    ev = threading.Event()

    def mock_rodar_backtest_lento():
        ev.wait(5)

    monkeypatch.setattr("app.consultor.avaliador_historico.rodar_backtest", mock_rodar_backtest_lento)
    import app.agendador
    app.agendador._backtest_thread = None

    for nome in ["ibovespa", "highlights", "mare", "volume_alerts", "dolar_correlation", "sensibilidade_juros", "forca_relativa", "escudo_quedas", "coesao", "atrasadas_rally", "concentracao", "apetite_risco", "variacao_subita", "concentracao_setorial", "rotacao_capital", "faca_caindo", "compradores_fundo", "armadilha_abertura", "sobrevivencia_semanal", "radar_anomalia_fechamento", "volatilidade_silenciosa", "scanner_capitulacao", "radar_inflexao", "anomalia_peso", "radar_short_squeeze", "radar_congestionamento", "radar_liquidez_abertura", "esforco_resultado", "radar_divergencia_volume", "fator_peso_pesado", "falso_rompimento", "radar_absorcao_cruzada", "motores_indice", "clima_global", "relogio_volatilidade", "radar_anomalias_spread", "concentracao_ordens", "exaustao_tendencia", "exaustao_queda", "radar_exaustao_alta", "divergencia_ibov_dolar", "correlacao_di", "assimetria_risco_retorno", "consultor_historico", "consultor_opinioes", "consultor_fechamento"]:
        monkeypatch.setattr(f"app.collectors.{nome}.collect_and_save", lambda: True)

    monkeypatch.setattr("datetime.datetime", type("MockDateTime", (), {"now": lambda tz: datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc)}))

    estado_detalhes_manual_1 = []
    _coletar(estado_detalhes_manual_1)

    estado_detalhes_manual_2 = []
    _coletar(estado_detalhes_manual_2)

    ev.set()
    if app.agendador._backtest_thread is not None:
        app.agendador._backtest_thread.join()

    assert any("consultor_historico: backtest anterior ainda em curso" in msg for msg in estado_detalhes_manual_2)
