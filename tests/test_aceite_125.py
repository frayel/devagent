from datetime import datetime, timezone, timedelta, date
import json
from app.agendador import intervalo
import app.banco
import app.agendador
from app.banco import get_connection

BRT = timezone(timedelta(hours=-3))


def get_row(painel, dt):
    conn, _ = get_connection()
    try:
        row = (
            conn.cursor()
            .execute(
                "SELECT estado, fonte, payload FROM snapshots_paineis WHERE painel = ? AND data_referencia = ?",
                (painel, str(dt)),
            )
            .fetchone()
        )
        return row
    finally:
        conn.close()


def test_intervalo_fechamento():
    agora_brt_18_40 = datetime(2023, 10, 23, 18, 40, tzinfo=BRT)  # Monday
    assert int(intervalo(agora_brt_18_40).total_seconds()) == 1800

    agora_brt_20_10 = datetime(2023, 10, 23, 20, 10, tzinfo=BRT)  # Monday
    assert int(intervalo(agora_brt_20_10).total_seconds()) == 7200


def test_marca_incompleto_sem_chamar_coletor(monkeypatch):
    agora = datetime(2023, 10, 23, 20, 5, tzinfo=BRT)
    monkeypatch.setattr("app.calendario.e_pregao", lambda x: True)
    monkeypatch.setattr("app.calendario.mercado_aberto", lambda x: False)
    monkeypatch.setattr("app.calendario.pregao_corrente", lambda x: date(2023, 10, 23))
    monkeypatch.setattr(
        "app.calendario.ultimo_pregao_fechado", lambda x: date(2023, 10, 23)
    )

    class MockDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz == timezone.utc:
                return agora.astimezone(timezone.utc)
            return super().now(tz)

    monkeypatch.setattr("app.agendador.datetime", MockDatetime)

    app.banco.gravar_snapshot(
        "ibovespa", date(2023, 10, 23), "ao_vivo", "mock_fonte", {"payload": "data"}
    )

    called_collectors = set()

    def mock_collect():
        called_collectors.add("ibovespa")
        return True

    monkeypatch.setattr("app.collectors.ibovespa.collect_and_save", mock_collect)

    def no_op():
        return True

    for nome in [
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
    ]:
        monkeypatch.setattr(f"app.collectors.{nome}.collect_and_save", no_op)

    app.agendador.coletar_tudo()

    assert "ibovespa" not in called_collectors

    row = get_row("ibovespa", date(2023, 10, 23))
    assert row is not None
    assert row[0] == "incompleto"
    assert row[1] == "mock_fonte"
    payload = json.loads(row[2])
    assert payload.get("payload") == {"payload": "data"}

    assert app.agendador.estado["detalhes"] is not None
    assert "ibovespa: incompleto" in app.agendador.estado["detalhes"]


def test_marca_incompleto_dia_seguinte(monkeypatch):
    agora = datetime(2023, 10, 24, 8, 0, tzinfo=BRT)  # Next day 08h00
    monkeypatch.setattr("app.calendario.e_pregao", lambda x: True)
    monkeypatch.setattr("app.calendario.mercado_aberto", lambda x: False)
    monkeypatch.setattr("app.calendario.pregao_corrente", lambda x: date(2023, 10, 24))
    monkeypatch.setattr(
        "app.calendario.ultimo_pregao_fechado", lambda x: date(2023, 10, 23)
    )

    class MockDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz == timezone.utc:
                return agora.astimezone(timezone.utc)
            return super().now(tz)

    monkeypatch.setattr("app.agendador.datetime", MockDatetime)

    app.banco.gravar_snapshot(
        "ibovespa", date(2023, 10, 23), "ao_vivo", "mock_fonte", {"payload": "data2"}
    )

    def no_op():
        return True

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
        "consultor_historico",
        "consultor_opinioes",
        "consultor_fechamento",
    ]:
        monkeypatch.setattr(f"app.collectors.{nome}.collect_and_save", no_op)

    app.agendador.coletar_tudo()

    row = get_row("ibovespa", date(2023, 10, 23))
    assert row is not None
    assert row[0] == "incompleto"
    assert json.loads(row[2]).get("payload") == {"payload": "data2"}


def test_final_continua_final(monkeypatch):
    agora = datetime(2023, 10, 23, 20, 5, tzinfo=BRT)
    monkeypatch.setattr("app.calendario.e_pregao", lambda x: True)
    monkeypatch.setattr("app.calendario.mercado_aberto", lambda x: False)
    monkeypatch.setattr("app.calendario.pregao_corrente", lambda x: date(2023, 10, 23))
    monkeypatch.setattr(
        "app.calendario.ultimo_pregao_fechado", lambda x: date(2023, 10, 23)
    )

    class MockDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz == timezone.utc:
                return agora.astimezone(timezone.utc)
            return super().now(tz)

    monkeypatch.setattr("app.agendador.datetime", MockDatetime)

    app.banco.gravar_snapshot(
        "ibovespa", date(2023, 10, 23), "final", "mock_fonte", {"payload": "data3"}
    )

    def no_op():
        return True

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
        "consultor_historico",
        "consultor_opinioes",
        "consultor_fechamento",
    ]:
        monkeypatch.setattr(f"app.collectors.{nome}.collect_and_save", no_op)

    app.agendador.coletar_tudo()

    row = get_row("ibovespa", date(2023, 10, 23))
    assert row is not None
    assert row[0] == "final"
    assert json.loads(row[2]).get("payload") == "data3"


def test_listar_datas_inclui_incompleto(monkeypatch):
    agora = datetime(2023, 10, 23, 20, 5, tzinfo=BRT)
    monkeypatch.setattr("app.calendario.e_pregao", lambda x: True)
    monkeypatch.setattr("app.calendario.mercado_aberto", lambda x: False)
    monkeypatch.setattr("app.calendario.pregao_corrente", lambda x: date(2023, 10, 23))
    monkeypatch.setattr(
        "app.calendario.ultimo_pregao_fechado", lambda x: date(2023, 10, 23)
    )

    class MockDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz == timezone.utc:
                return agora.astimezone(timezone.utc)
            return super().now(tz)

    monkeypatch.setattr("app.agendador.datetime", MockDatetime)

    app.banco.gravar_snapshot(
        "ibovespa", date(2023, 10, 23), "incompleto", "mock_fonte", {"payload": "data"}
    )

    datas = app.banco.listar_datas("ibovespa")
    assert str(date(2023, 10, 23)) in datas
