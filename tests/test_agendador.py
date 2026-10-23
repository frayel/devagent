from datetime import datetime, timedelta, timezone

from app import agendador


def test_intervalo_no_pregao_e_fora():
    quarta_14h_brt = datetime(2026, 9, 23, 17, 0, tzinfo=timezone.utc)
    quarta_22h_brt = datetime(2026, 9, 24, 1, 0, tzinfo=timezone.utc)
    sabado = datetime(2026, 9, 26, 17, 0, tzinfo=timezone.utc)
    assert agendador.intervalo(quarta_14h_brt) == timedelta(minutes=15)
    assert agendador.intervalo(quarta_22h_brt) == timedelta(hours=2)
    assert agendador.intervalo(sabado) == timedelta(hours=2)


def test_coleta_desligada_nos_testes():
    assert agendador.coleta_ligada() is False


def test_falha_de_um_coletor_nao_impede_o_outro(monkeypatch):
    monkeypatch.setattr("app.collectors.anomalia_peso.collect_and_save", lambda: True)
    monkeypatch.setattr("app.collectors.radar_inflexao.collect_and_save", lambda: True)
    monkeypatch.setattr(
        "app.collectors.divergencia_ibov_dolar.collect_and_save", lambda: True
    )
    monkeypatch.setattr(
        "app.collectors.assimetria_risco_retorno.collect_and_save", lambda: True
    )
    monkeypatch.setattr("app.collectors.forca_relativa.collect_and_save", lambda: True)
    chamados = []
    monkeypatch.setattr("app.collectors.coesao.collect_and_save", lambda: True)
    monkeypatch.setattr("app.collectors.atrasadas_rally.collect_and_save", lambda: True)
    monkeypatch.setattr("app.collectors.faca_caindo.collect_and_save", lambda: True)
    monkeypatch.setattr(
        "app.collectors.compradores_fundo.collect_and_save", lambda: True
    )
    monkeypatch.setattr(
        "app.collectors.armadilha_abertura.collect_and_save", lambda: True
    )
    monkeypatch.setattr(
        "app.collectors.sobrevivencia_semanal.collect_and_save", lambda: True
    )

    def quebra():
        chamados.append("ibovespa")
        raise RuntimeError("fonte fora")

    def funciona():
        chamados.append("highlights")
        return True

    def funciona_volume():
        chamados.append("volume_alerts")
        return True

    monkeypatch.setattr(
        "app.collectors.radar_liquidez_abertura.collect_and_save", lambda: True
    )
    monkeypatch.setattr(
        "app.collectors.esforco_resultado.collect_and_save", lambda: True
    )
    monkeypatch.setattr(
        "app.collectors.fator_peso_pesado.collect_and_save", lambda: True
    )
    monkeypatch.setattr(
        "app.collectors.radar_divergencia_volume.collect_and_save", lambda: True
    )
    monkeypatch.setattr(
        "app.collectors.falso_rompimento.collect_and_save", lambda: True
    )

    monkeypatch.setattr("app.collectors.escudo_quedas.collect_and_save", lambda: True)
    monkeypatch.setattr("app.collectors.clima_global.collect_and_save", lambda: True)
    monkeypatch.setattr(
        "app.collectors.concentracao_ordens.collect_and_save", lambda: True
    )
    monkeypatch.setattr("app.collectors.concentracao.collect_and_save", lambda: True)
    monkeypatch.setattr(
        "app.collectors.concentracao_setorial.collect_and_save", lambda: True
    )
    monkeypatch.setattr("app.collectors.apetite_risco.collect_and_save", lambda: True)
    monkeypatch.setattr("app.collectors.mare.collect_and_save", lambda: True)
    monkeypatch.setattr("app.collectors.variacao_subita.collect_and_save", lambda: True)
    monkeypatch.setattr("app.collectors.rotacao_capital.collect_and_save", lambda: True)
    monkeypatch.setattr(
        "app.collectors.scanner_capitulacao.collect_and_save", lambda: True
    )
    monkeypatch.setattr(
        "app.collectors.relogio_volatilidade.collect_and_save", lambda: True
    )
    monkeypatch.setattr("app.collectors.motores_indice.collect_and_save", lambda: True)
    monkeypatch.setattr(
        "app.collectors.sensibilidade_juros.collect_and_save", lambda: True
    )
    monkeypatch.setattr(
        "app.collectors.radar_anomalias_spread.collect_and_save", lambda: True
    )
    monkeypatch.setattr(
        "app.collectors.exaustao_tendencia.collect_and_save", lambda: True
    )
    monkeypatch.setattr("app.collectors.exaustao_queda.collect_and_save", lambda: True)
    monkeypatch.setattr(
        "app.collectors.radar_anomalia_fechamento.collect_and_save", lambda: True
    )
    monkeypatch.setattr(
        "app.collectors.radar_short_squeeze.collect_and_save", lambda: True
    )
    monkeypatch.setattr(
        "app.collectors.consultor_historico.collect_and_save", lambda: True
    )

    monkeypatch.setattr("app.collectors.ibovespa.collect_and_save", quebra)
    monkeypatch.setattr("app.collectors.highlights.collect_and_save", funciona)
    monkeypatch.setattr(
        "app.collectors.volume_alerts.collect_and_save", funciona_volume
    )

    def funciona_dolar():
        chamados.append("dolar_correlation")
        return True

    monkeypatch.setattr(
        "app.collectors.dolar_correlation.collect_and_save", funciona_dolar
    )
    agendador.coletar_tudo()
    assert chamados == ["ibovespa", "highlights", "volume_alerts", "dolar_correlation"]
    assert "fonte fora" in (agendador.estado["ultimo_erro"] or "")
    assert agendador.estado["ultima_coleta"] is not None


def test_httpx_e_dependencia_de_producao():
    """Regressão: os coletores importam httpx; sem ele em requirements.txt,
    a coleta quebra em produção mesmo com os testes passando."""
    with open("requirements.txt") as f:
        assert "httpx" in {linha.strip().split("=")[0] for linha in f}


def test_mascara_token_no_estado(monkeypatch):
    from app import agendador
    import httpx

    agendador.estado["ultimo_erro"] = None
    agendador.estado["detalhes"] = None

    def quebra():
        raise httpx.RequestError(
            "Falha na url https://api.com/?token=SEGREDO_123&range=1d",
            request=httpx.Request("GET", "https://api.com/?token=SEGREDO_123&range=1d"),
        )

    monkeypatch.setattr("app.collectors.ibovespa.collect_and_save", quebra)

    # Mocking others to just return True
    for nome in (
        "highlights",
        "mare",
        "volume_alerts",
        "dolar_correlation",
        "sensibilidade_juros",
        "motores_indice",
        "relogio_volatilidade",
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
        "volatilidade_silenciosa",
        "scanner_capitulacao",
        "radar_inflexao",
        "divergencia_ibov_dolar",
        "assimetria_risco_retorno",
        "anomalia_peso",
        "radar_short_squeeze",
        "radar_congestionamento",
        "esforco_resultado",
        "radar_divergencia_volume",
        "falso_rompimento",
        "radar_liquidez_abertura",
        "radar_absorcao_cruzada",
        "fator_peso_pesado",
        "clima_global",
        "radar_anomalias_spread",
        "concentracao_ordens",
        "exaustao_tendencia",
        "radar_anomalia_fechamento",
        "consultor_historico",
        "exaustao_queda",
        "fator_mola",
    ):
        monkeypatch.setattr(f"app.collectors.{nome}.collect_and_save", lambda: True)

    agendador.coletar_tudo()

    assert "SEGREDO_123" not in agendador.estado["ultimo_erro"]
    assert "token=***" in agendador.estado["ultimo_erro"]

    if agendador.estado["detalhes"] is not None:
        assert "SEGREDO_123" not in agendador.estado["detalhes"]
        assert (
            "token=***" in agendador.estado["detalhes"]
            or "Error fetching" in agendador.estado["detalhes"]
            or "partida_a_frio" in agendador.estado["detalhes"]
        )


def test_estado_detalhes_masking(monkeypatch):
    import app.agendador

    class FakeMemoria:
        def __init__(self):
            self.linhas = ["Error: http://api.com?token=supersecret"]

    monkeypatch.setattr("app.agendador._Memoria", FakeMemoria)
    monkeypatch.setattr("app.agendador._coletar", lambda e=None: None)

    # Needs a fake logger handler mock, let's just mock the handler remove
    import logging

    raiz = logging.getLogger("app.collectors")

    monkeypatch.setattr(raiz, "removeHandler", lambda x: None)
    monkeypatch.setattr(raiz, "addHandler", lambda x: None)

    app.agendador.coletar_tudo()

    assert "supersecret" not in app.agendador.estado["detalhes"]
    assert "***" in app.agendador.estado["detalhes"]
