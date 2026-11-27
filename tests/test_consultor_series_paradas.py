"""Regressão do Consultor vazio de 17/11 a 27/11/2026.

A série diária de 2 anos parou de ser renovada: fora do pregão o cache nunca
vencia, e o coletor só rodava no sábado. Durante o pregão a página descartava
a série velha e escondia também as opiniões; o /sistema não tinha item que
olhasse a idade da série.
"""

from datetime import datetime, timedelta, timezone

import httpx

import app.banco as banco
import app.database as db
from app.collectors import utils

SEXTA_FECHADA = datetime(2026, 11, 27, 23, 0, tzinfo=timezone.utc)  # 20h BRT
SEXTA_ABERTA = datetime(2026, 11, 27, 16, 30, tzinfo=timezone.utc)  # 13h30 BRT
DEZ_DIAS_ANTES = datetime(2026, 11, 18, 0, 2, tzinfo=timezone.utc)


def test_serie_velha_vence_mesmo_com_o_mercado_fechado():
    assert db.serie_vencida(DEZ_DIAS_ANTES, SEXTA_FECHADA, 60, aberto=False)


def test_serie_coletada_depois_do_ultimo_fechamento_vale_a_noite_toda():
    depois_do_fechamento = datetime(2026, 11, 27, 21, 30, tzinfo=timezone.utc)
    madrugada = datetime(2026, 11, 28, 6, 0, tzinfo=timezone.utc)
    assert not db.serie_vencida(depois_do_fechamento, madrugada, 60, aberto=False)


def test_serie_dentro_da_idade_nao_vence():
    recente = SEXTA_ABERTA - timedelta(minutes=10)
    assert not db.serie_vencida(recente, SEXTA_ABERTA, 15, aberto=True)


def test_coletor_renova_serie_velha_fora_do_pregao(monkeypatch):
    """Antes da correção, devolvia o cache de 10 dias sem chamar o Yahoo."""
    with monkeypatch.context() as m:
        m.setattr(banco, "datetime", _Relogio(DEZ_DIAS_ANTES))
        banco.gravar_serie("^BVSP", [{"data": "2026-11-17", "close": 150000.0}])
    db._historico_diario_cache.clear()
    monkeypatch.setattr("app.calendario.mercado_aberto", lambda agora: False)
    pedidos: list[str] = []

    def falso(url, client):
        pedidos.append(url)
        raise httpx.ConnectError("fora")

    monkeypatch.setattr(utils, "fetch_with_retry", falso)
    with httpx.Client() as client:
        dado = utils.fetch_historico_diario_yfinance_chart(
            "^BVSP", "2y", "1d", client, max_age_minutes=60
        )
    assert pedidos, "a série velha deveria ter sido pedida de novo ao Yahoo"
    assert dado is None


class _Relogio:
    """Troca `datetime.now()` do `gravar_serie` para gravar no passado."""

    def __init__(self, instante: datetime):
        self.instante = instante

    def now(self, tz=None):
        return self.instante if tz else self.instante.replace(tzinfo=None)

    def __getattr__(self, nome):
        return getattr(datetime, nome)


def test_sem_serie_do_ibovespa_as_opinioes_continuam(monkeypatch):
    from app.consultor import calculador

    opiniao = {
        "ticker": "PETR4",
        "casa": "XP",
        "recomendacao": "compra",
        "extraida_em": "2026-11-27T13:20:00+00:00",
    }
    monkeypatch.setattr(calculador, "get_historico_diario", lambda *a, **k: {})
    monkeypatch.setattr(calculador, "get_opinioes_recentes", lambda: [opiniao])
    monkeypatch.setattr(calculador, "get_opinioes_ativos", lambda: {})
    monkeypatch.setattr(calculador, "_consultor_cache", None)

    dados = calculador.calcular_consultor(ignorar_cache=True)

    assert dados["sinais_indisponiveis"] is True
    assert dados["ativos_avaliados"] == 0
    assert dados["opinioes_recentes"] == [opiniao]


def test_pagina_explica_por_que_nao_ha_sinais(monkeypatch):
    from fastapi.testclient import TestClient

    import app.main

    monkeypatch.delenv("CONSULTOR_SENHA", raising=False)
    monkeypatch.setattr(
        app.main,
        "calcular_consultor",
        lambda: {
            "sinais_indisponiveis": True,
            "ativos_avaliados": 0,
            "opinioes_recentes": [],
            "opinioes_por_ativo": [],
            "regras_confianca": {},
            "opinioes_status": {},
            "sinais_pregao": None,
            "sinais_coletado_em": "2026-11-18T00:02:00+00:00",
        },
    )
    html = TestClient(app.main.app).get("/consultor").text
    assert 'id="consultor-sem-series"' in html
    assert "regras técnicas não foram avaliadas" in html


def test_backtest_continua_semanal(monkeypatch):
    from app import agendador

    agora = datetime(2026, 11, 27, 21, 30, tzinfo=timezone.utc)
    monkeypatch.setattr(
        "app.database.get_consultor_confianca",
        lambda: {"R1": {"atualizado_em": agora - timedelta(days=2)}},
    )
    assert not agendador.backtest_vencido(agora)
    monkeypatch.setattr(
        "app.database.get_consultor_confianca",
        lambda: {"R1": {"atualizado_em": agora - timedelta(days=7)}},
    )
    assert agendador.backtest_vencido(agora)
    monkeypatch.setattr("app.database.get_consultor_confianca", lambda: {})
    assert agendador.backtest_vencido(agora)


def test_sistema_acusa_serie_parada():
    from app.services import sistema

    item = sistema.verificar_series_consultor("2026-11-18 00:02:00+00:00", SEXTA_ABERTA)
    assert item.nivel == sistema.PROBLEMA
    assert "pregões sem renovar" in item.resumo


def test_sistema_serie_de_dois_pregoes_e_atencao():
    from app.services import sistema

    # Coletada depois do fechamento de 24/11; 25/11 e 26/11 fecharam sem ela.
    item = sistema.verificar_series_consultor("2026-11-24 21:30:00+00:00", SEXTA_ABERTA)
    assert item.nivel == sistema.ATENCAO


def test_sistema_serie_em_dia_e_ok():
    from app.services import sistema

    item = sistema.verificar_series_consultor("2026-11-26 21:30:00+00:00", SEXTA_ABERTA)
    assert item.nivel == sistema.OK


def test_sistema_sem_serie_e_problema():
    from app.services import sistema

    assert sistema.verificar_series_consultor("", SEXTA_ABERTA).nivel == (
        sistema.PROBLEMA
    )
