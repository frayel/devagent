"""Aceite da spec 174a: o humor médio do último mês e do último ano.

Sem rede: cálculo com leituras sintéticas, coletor com o Yahoo falso de
`tests/yahoo_falso.py` e agendamento com o relógio fixado.
"""

from __future__ import annotations

import importlib
from datetime import date, datetime, timedelta, timezone

import httpx
import pytest
from fastapi.testclient import TestClient

import app.banco
import app.database
from app import agendador, calendario
from app.collectors import mare_historico
from app.services import mare
from devagent.aceite import exigir_spec_done
from tests import yahoo_falso


@pytest.fixture(autouse=True)
def _spec_done():
    exigir_spec_done("174a")


def _leituras(valores, fluxo_presente=None, inicio=date(2026, 1, 1)):
    saida = []
    for i, v in enumerate(valores):
        tem_fluxo = fluxo_presente is None or i < fluxo_presente
        saida.append(
            {
                "data": (inicio + timedelta(days=i)).isoformat(),
                "valor": v,
                "fluxo": 70.0 if tem_fluxo else None,
                "calma": 48.0,
                "volume": 62.0,
            }
        )
    return saida


# --- cálculo ---------------------------------------------------------------


def test_valor_do_nivel_e_a_media_arredondada():
    leituras = _leituras([50] * 20 + [61])
    ondas = mare.nivel(leituras, 21, 15)
    assert ondas is not None
    assert ondas["valor"] == 51
    assert ondas["faixa"] == mare.faixa(51)
    assert ondas["pregoes"] == 21
    assert ondas["de"] == leituras[0]["data"]
    assert ondas["ate"] == leituras[-1]["data"]


def test_minimo_de_leituras():
    niveis = mare.niveis({"leituras": _leituras([50] * 14)})
    assert niveis["ondas"] is None
    assert niveis["mare"] is None

    niveis = mare.niveis({"leituras": _leituras([50] * 188)})
    assert niveis["mare"] is None
    assert niveis["ondas"] is not None
    assert niveis["ondas"]["pregoes"] == 21

    niveis = mare.niveis({"leituras": _leituras([50] * 200)})
    assert niveis["mare"]["pregoes"] == 200


def test_componente_presente_em_menos_de_75_por_cento_fica_ausente():
    ondas = mare.nivel(_leituras([50] * 21, fluxo_presente=15), 21, 15)
    assert ondas["componentes"]["fluxo"] is None
    assert ondas["ausentes"] == ["fluxo"]
    assert ondas["componentes"]["calma"] == 48.0
    assert ondas["componentes"]["volume"] == 62.0
    assert ondas["pesos"]["calma"] == pytest.approx(0.5833, abs=1e-4)
    assert ondas["pesos"]["volume"] == pytest.approx(0.4167, abs=1e-4)
    assert sum(ondas["pesos"].values()) == pytest.approx(1, abs=0.001)

    ondas = mare.nivel(_leituras([50] * 21, fluxo_presente=16), 21, 15)
    assert ondas["componentes"]["fluxo"] == 70.0
    assert ondas["ausentes"] == []


# --- heatmap ---------------------------------------------------------------


def test_heatmap_da_janela_bate_com_a_conta_a_mao():
    dias = [date(2026, 1, 1) + timedelta(days=i) for i in range(22)]
    anterior, janela = dias[0], dias[1:]
    acoes = {
        # Fecha 30,00 antes da janela e 31,50 no último pregão: +5%.
        "PETR4": {
            d: (30.0 if d == anterior else (31.5 if d == janela[-1] else 31.0), 1e7)
            for d in dias
        },
        "VALE3": {d: (50.0 if d == anterior else 45.0, 1e6) for d in dias},
        "ITUB4": {d: (20.0, 3e6) for d in dias},
    }
    heat = mare.heatmap_janela(acoes, janela, anterior)

    assert [a["ticker"] for a in heat] == ["PETR4", "ITUB4", "VALE3"]
    petr = heat[0]
    assert petr["variacao"] == pytest.approx(5.0)
    assert petr["financeiro"] == pytest.approx(20 * 31.0 * 1e7 + 31.5 * 1e7)
    assert heat[2]["variacao"] == pytest.approx(-10.0)
    total = sum(a["financeiro"] for a in heat)
    assert petr["peso"] == pytest.approx(petr["financeiro"] / total)
    assert sum(a["peso"] for a in heat) == pytest.approx(1.0)


def test_acao_sem_fechamento_antes_da_janela_fica_de_fora():
    dias = [date(2026, 1, 1) + timedelta(days=i) for i in range(22)]
    acoes = {"NOVA3": {d: (10.0, 1e6) for d in dias[1:]}}
    assert mare.heatmap_janela(acoes, dias[1:], dias[0]) == []


# --- coletor ---------------------------------------------------------------


def test_coletor_grava_historico_com_o_yahoo_falso(monkeypatch):
    yahoo_falso.instalar(monkeypatch)

    assert mare_historico.collect_and_save() is True

    payload = app.banco.ler_snapshot("mare_historico")
    assert payload is not None
    leituras = payload["leituras"]
    assert 0 < len(leituras) <= 252
    datas = [x["data"] for x in leituras]
    assert datas == sorted(datas)
    ultimo = calendario.ultimo_pregao_fechado(datetime.now(timezone.utc))
    assert all(date.fromisoformat(d) <= ultimo for d in datas)
    assert payload["ate"] == datas[-1]
    assert len(payload["heatmap_ondas"]) <= 10
    assert len(payload["heatmap_mare"]) <= 10


# --- agendamento -------------------------------------------------------------


def _relogio(instante: datetime) -> type[datetime]:
    class _Relogio(datetime):
        @classmethod
        def now(cls, tz=None):  # type: ignore[override]
            return instante if tz is None else instante.astimezone(tz)

    return _Relogio


def _rodar(monkeypatch, instante, chamadas: list[str]) -> None:
    class _Coletor:
        @staticmethod
        def collect_and_save():
            chamadas.append("mare_historico")
            app.banco.gravar_snapshot(
                "mare_historico",
                instante.date(),  # o agendador força o último pregão completo
                "final",
                "teste",
                {"leituras": [], "ate": "2026-11-17"},
            )
            return True

    def importar(nome):
        if nome.rsplit(".", 1)[-1] == "mare_historico":
            return _Coletor
        raise ImportError("coletor fora do teste")

    monkeypatch.setattr(importlib, "import_module", importar)
    monkeypatch.setattr(agendador, "datetime", _relogio(instante))
    monkeypatch.setattr(agendador, "_avisar_falha", lambda *a, **k: None)
    monkeypatch.setattr(agendador, "_registrar_erro", lambda *a, **k: None)
    monkeypatch.setattr(
        app.database, "gravar_instrumentacao_rodada", lambda *a, **k: None
    )
    agendador._coletar()


# Terça, 17/11/2026: 18h30 e 19h00 BRT, e 11h00 BRT da quarta.
H1830 = datetime(2026, 11, 17, 21, 30, tzinfo=timezone.utc)
H1900 = datetime(2026, 11, 17, 22, 0, tzinfo=timezone.utc)
QUARTA_11H = datetime(2026, 11, 18, 14, 0, tzinfo=timezone.utc)


def test_roda_uma_vez_por_pregao_depois_do_fechamento(monkeypatch):
    chamadas: list[str] = []
    _rodar(monkeypatch, H1830, chamadas)
    assert chamadas == ["mare_historico"]
    assert app.banco.ler_snapshot("mare_historico", date(2026, 11, 17)) is not None

    _rodar(monkeypatch, H1900, chamadas)
    assert chamadas == ["mare_historico"]


def test_nao_roda_com_o_mercado_aberto_e_snapshot_presente(monkeypatch):
    app.banco.gravar_snapshot(
        "mare_historico", date(2026, 11, 17), "final", "teste", {"leituras": []}
    )
    chamadas: list[str] = []
    _rodar(monkeypatch, QUARTA_11H, chamadas)
    assert chamadas == []


# --- plano B -----------------------------------------------------------------


def test_yahoo_429_nao_grava_e_snapshot_mantem_os_niveis(monkeypatch):
    from app.collectors import utils

    app.banco.gravar_snapshot(
        "mare_historico",
        date(2026, 11, 16),
        "final",
        "yfinance",
        {"leituras": _leituras([50] * 20 + [61]), "ate": "2026-01-21"},
    )

    enviar_original = httpx.Client.send

    def recusar(self, request, *args, **kwargs):
        return httpx.Response(429, request=request)

    monkeypatch.setattr(httpx.Client, "send", recusar)
    monkeypatch.setattr(utils, "_enforce_rate_limit", lambda dominio: None)
    monkeypatch.setattr(utils.time, "sleep", lambda s: None)

    assert mare_historico.collect_and_save() is False
    assert app.banco.listar_datas("mare_historico", 5) == ["2026-11-16"]

    monkeypatch.setattr(httpx.Client, "send", enviar_original)
    from app.main import app as aplicacao

    snap = TestClient(aplicacao).get("/api/snapshot").json()
    assert snap["paineis"]["mare"]["niveis"]["ondas"]["valor"] == 51
    assert snap["paineis"]["mare"]["niveis"]["mare"] is None


def test_sem_historico_niveis_nulos_e_resto_da_mare_igual():
    from app.main import app as aplicacao

    cliente = TestClient(aplicacao)
    mare_snap = cliente.get("/api/snapshot").json()["paineis"]["mare"]
    assert mare_snap["niveis"] == {"ondas": None, "mare": None}
    resto = {k: v for k, v in mare_snap.items() if k != "niveis"}
    assert set(resto) == {"fonte", "coletado_em"}
