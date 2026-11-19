"""Aceite da spec 186: a confluência de cada pregão fica guardada.

Sem rede, com o SQLite temporário do `conftest`: as funções puras com os
payloads do exemplo, o coletor com snapshots de radares gravados no banco e
o relógio congelado, e a tela e o `/api/snapshot` com um `confluencia_historico`
gravado.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime, timezone

import pytest
from fastapi.testclient import TestClient

import app.banco
from app import agendador
from app.collectors import confluencia_historico
from app.main import app as aplicacao
from app.services.radares import (
    RADARES,
    acumular,
    confluencia,
    registro_do_pregao,
)
from devagent.aceite import exigir_spec_done
from tests.test_aceite_150 import _historico
from tests.test_aceite_155 import T_1030, _card, _exemplo, _faca
from tests.test_aceite_155 import radares as radares  # noqa: F401 - fixture

client = TestClient(aplicacao)

PREGAO = date(2026, 11, 18)
REGISTRO_EXEMPLO = {
    "data": "2026-11-18",
    "lidos": 17,
    "acoes": [
        {
            "ticker": "PETR4",
            "radares": ["Radar de volume", "Variação Súbita", "Radar de Faca Caindo"],
        },
        {"ticker": "VALE3", "radares": ["Radar de volume", "Radar de Faca Caindo"]},
    ],
}


@pytest.fixture(autouse=True)
def _spec_done():
    exigir_spec_done("186")


def _payloads_exemplo() -> dict:
    ts = datetime(2026, 11, 18, 20, 0, tzinfo=timezone.utc)
    payloads: dict = {
        chave: {"timestamp": ts, campo: []} for chave, _n, campo in RADARES
    }
    payloads["volume_alerts"] = {
        "timestamp": ts,
        "alerts": [{"ticker": "PETR4.SA"}, {"ticker": "VALE3"}],
    }
    payloads["variacao_subita"] = {"timestamp": ts, "alertas": [{"ticker": "PETR4"}]}
    payloads["faca_caindo"] = {
        "timestamp": ts,
        "alertas": [{"ticker": " petr4 "}, {"ticker": "VALE3"}, {"ticker": "ITUB4"}],
    }
    for chave in ("radar_inflexao", "short_squeeze", "radar_congestionamento"):
        payloads[chave] = None
    return payloads


# --- funções puras ------------------------------------------------------------


def test_registro_do_exemplo():
    assert registro_do_pregao(_payloads_exemplo(), PREGAO) == REGISTRO_EXEMPLO


def test_registro_sem_leitura_e_none():
    vazios = {chave: None for chave, _n, _c in RADARES}
    assert registro_do_pregao(vazios, PREGAO) is None


def test_confluencia_sem_limite():
    ts = datetime(2026, 11, 18, 20, 0, tzinfo=timezone.utc)
    itens = [{"ticker": f"AAAA{i:02d}"} for i in range(12)]
    ctx = {
        "volume_alerts": {"timestamp": ts, "alerts": itens},
        "faca_caindo": {"timestamp": ts, "alertas": itens},
    }
    todas = confluencia(ctx, ts, True, limite=None)
    assert len(todas["acoes"]) == 12 and todas["excedentes"] == 0
    padrao = confluencia(ctx, ts, True)
    assert len(padrao["acoes"]) == 10 and padrao["excedentes"] == 2


def _r(d: str, lidos: int = 1) -> dict:
    return {"data": d, "lidos": lidos, "acoes": []}


def test_acumular():
    anterior = [_r("2026-11-13"), _r("2026-11-17", 5)]
    novos = [_r("2026-11-17", 9), _r("2026-11-16")]
    juntos = acumular(anterior, novos)
    assert [r["data"] for r in juntos] == ["2026-11-13", "2026-11-16", "2026-11-17"]
    assert juntos[-1]["lidos"] == 9
    cinco = [_r(f"2026-11-1{i}") for i in range(5)]
    assert [r["data"] for r in acumular(cinco, [], maximo=3)] == [
        "2026-11-12",
        "2026-11-13",
        "2026-11-14",
    ]


# --- coletor -----------------------------------------------------------------


@pytest.fixture
def relogio_19h(monkeypatch):
    """Quarta, 18/11/2026, 19h BRT: o último pregão fechado é o próprio dia."""

    class Relogio(datetime):
        @classmethod
        def now(cls, tz=None):  # type: ignore[override]
            agora = datetime(2026, 11, 18, 22, 0, tzinfo=timezone.utc)
            return agora if tz is None else agora.astimezone(tz)

    monkeypatch.setattr(confluencia_historico, "datetime", Relogio)


_ITENS = {
    "volume_alerts": lambda t: {"ticker": t, "ratio": 2.0, "price": 30.0},
    "faca_caindo": _faca,
}


def _gravar_radar(painel: str, dia: date, campo: str, tickers: list[str]) -> None:
    ts = datetime(dia.year, dia.month, dia.day, 20, 0, tzinfo=timezone.utc)
    payload = {
        "timestamp": ts.isoformat(),
        campo: json.dumps([_ITENS[painel](t) for t in tickers]),
        "fonte": "teste",
    }
    app.banco.gravar_snapshot(painel, dia, "final", "teste", payload)


def _historico_gravado() -> dict | None:
    return app.banco.ler_snapshot("confluencia_historico", PREGAO)


def test_coletor_guarda_os_pregoes_lidos(relogio_19h):
    # 18/11 e 16/11 com radares gravados; 17/11 sem nenhum snapshot de radar.
    _gravar_radar("volume_alerts", PREGAO, "alerts_json", ["PETR4", "VALE3"])
    _gravar_radar("faca_caindo", PREGAO, "alertas_json", ["PETR4"])
    _gravar_radar("volume_alerts", date(2026, 11, 16), "alerts_json", ["ITUB4"])

    assert confluencia_historico.collect_and_save() is True
    snap = _historico_gravado()
    assert snap is not None
    datas = [r["data"] for r in snap["registros"]]
    assert datas == ["2026-11-16", "2026-11-18"]
    assert snap["de"] == "2026-11-16" and snap["ate"] == "2026-11-18"
    assert snap["fonte"] == "composto" and snap["coletado_em"]
    ultimo = snap["registros"][-1]
    assert ultimo["lidos"] == 2
    assert ultimo["acoes"] == [
        {"ticker": "PETR4", "radares": ["Radar de volume", "Radar de Faca Caindo"]}
    ]

    # Os snapshots do 18/11 mudam: o registro guardado não é recalculado.
    _gravar_radar("faca_caindo", PREGAO, "alertas_json", ["VALE3"])
    assert confluencia_historico.collect_and_save() is True
    assert _historico_gravado()["registros"][-1] == ultimo


def test_coletor_sem_nada_nao_grava(relogio_19h):
    assert confluencia_historico.collect_and_save() is False
    assert _historico_gravado() is None


def test_agendador_roda_por_ultimo():
    import inspect

    fonte = inspect.getsource(agendador._coletar)
    assert '"confluencia_historico": "diario"' in fonte
    tupla = re.search(r"for nome in \((.*?)\):", fonte, re.S)
    assert tupla
    nomes = re.findall(r'"([a-z_]+)"', tupla.group(1))
    assert nomes[-1] == "confluencia_historico"


# --- tela e /api/snapshot -----------------------------------------------------


def _gravar_historico(datas: list[str]) -> None:
    registros = [_r(d, 17) for d in datas[:-1]] + [REGISTRO_EXEMPLO]
    payload = {
        "registros": registros,
        "de": registros[0]["data"],
        "ate": registros[-1]["data"],
        "fonte": "composto",
        "coletado_em": "2026-11-18T22:00:00+00:00",
    }
    app.banco.gravar_snapshot(
        "confluencia_historico", PREGAO, "final", "composto", payload
    )


EXEMPLO = ["2026-11-13", "2026-11-14", "2026-11-17", "2026-11-18"]


def test_card_mostra_a_memoria(radares):  # noqa: F811
    _exemplo(radares)
    _gravar_historico(EXEMPLO)
    card = _card(client.get("/").text)
    assert "Guardada a cada fechamento: 4 pregões, desde 13/11/2026." in card


def test_card_com_um_pregao(radares):  # noqa: F811
    _exemplo(radares)
    _gravar_historico(["2026-11-18"])
    card = _card(client.get("/").text)
    assert "Guardada a cada fechamento: 1 pregão, desde 18/11/2026." in card


def test_card_sem_snapshot(radares):  # noqa: F811
    _exemplo(radares)
    html = client.get("/").text
    _card(html)
    assert "confluencia-memoria" not in html


def test_card_em_data_historica(radares, monkeypatch):  # noqa: F811
    monkeypatch.setattr("app.main._get_seletor_context", _historico(monkeypatch))
    _exemplo(radares)
    _gravar_historico(EXEMPLO)
    html = client.get("/?data=2026-11-18").text
    _card(html)
    assert "confluencia-memoria" not in html


def test_snapshot_traz_a_memoria(radares):  # noqa: F811
    _exemplo(radares)
    _gravar_historico(EXEMPLO)
    painel = client.get("/api/snapshot").json()["paineis"]["confluencia_historico"]
    assert painel["pregoes"] == 4
    assert painel["de"] == "2026-11-13" and painel["ate"] == "2026-11-18"
    assert painel["ultimo"] == REGISTRO_EXEMPLO
    assert painel["fonte"] == "composto"
    assert painel["coletado_em"] == "2026-11-18T22:00:00+00:00"


def test_snapshot_sem_memoria(radares):  # noqa: F811
    radares["faca_caindo"] = _snap_faca()
    painel = client.get("/api/snapshot").json()["paineis"]["confluencia_historico"]
    assert painel["pregoes"] == 0 and painel["ultimo"] is None
    assert painel["de"] is None and painel["ate"] is None
    assert painel["fonte"] == "composto" and painel["coletado_em"]


def _snap_faca():
    from tests.test_aceite_150 import _snap

    return _snap("faca_caindo", T_1030, [_faca("PETR4")])
