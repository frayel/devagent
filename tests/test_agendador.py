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
    monkeypatch.setattr("app.collectors.forca_relativa.collect_and_save", lambda: True)
    chamados = []

    def quebra():
        chamados.append("ibovespa")
        raise RuntimeError("fonte fora")

    def funciona():
        chamados.append("highlights")
        return True

    def funciona_volume():
        chamados.append("volume_alerts")
        return True

    monkeypatch.setattr("app.collectors.escudo_quedas.collect_and_save", lambda: True)
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
