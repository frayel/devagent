"""Aceite da spec 152: a instrumentação da coleta grava uma vez por rodada.

`_coletar` acumula em memória a duração de cada coletor e os que voltaram
vazios, e no fim da rodada `gravar_instrumentacao_rodada` faz uma leitura e uma
gravação do snapshot `instrumentacao`. Sem rede: os coletores são falsos e o
banco é o SQLite temporário do conftest.
"""

from __future__ import annotations

import importlib
from datetime import datetime, timezone

import pytest

import app.banco
from app import agendador, calendario
from app.database import gravar_instrumentacao_rodada
from devagent.aceite import exigir_spec_done

# Domingo, 15/11/2026, 12:00 BRT: o dia em BRT do snapshot é 15/11.
TIMESTAMP = datetime(2026, 11, 15, 15, 0, tzinfo=timezone.utc)
DIA = TIMESTAMP.date()

ANTES = {
    "tempos": {"ibovespa": 1.8},
    "vazias": {"mare": 2},
    "rodadas": {"ibovespa": 10, "mare": 10},
}
DEPOIS = {
    "tempos": {"ibovespa": 2.0, "mare": 1.5, "highlights": 59.0},
    "vazias": {"mare": 3},
    "rodadas": {"ibovespa": 11, "mare": 11, "highlights": 1},
}


@pytest.fixture(autouse=True)
def _spec_done():
    exigir_spec_done("152")


def _coletor(ok: bool, falha: bool = False):
    class _Coletor:
        @staticmethod
        def collect_and_save():
            if falha:
                raise RuntimeError("coletor quebrou no meio")
            return ok

    return _Coletor


class _Espiao:
    """Conta leituras e gravações do painel `instrumentacao`."""

    def __init__(self, monkeypatch, gravar_falha: bool = False):
        self.leituras = 0
        self.gravacoes: list[dict] = []
        ler_original = app.banco.ler_snapshot
        gravar_original = app.banco.gravar_snapshot

        def ler(painel, data_referencia=None):
            if painel == "instrumentacao":
                self.leituras += 1
            return ler_original(painel, data_referencia)

        def gravar(painel, *args, **kwargs):
            if painel == "instrumentacao":
                if gravar_falha:
                    raise RuntimeError("banco fora do ar")
                self.gravacoes.append(args[-1])
            return gravar_original(painel, *args, **kwargs)

        monkeypatch.setattr(app.banco, "ler_snapshot", ler)
        monkeypatch.setattr(app.banco, "gravar_snapshot", gravar)


def _isolar_coletores(monkeypatch, coletores: dict) -> None:
    def importar(nome):
        curto = nome.rsplit(".", 1)[-1]
        if curto in coletores:
            return coletores[curto]
        raise ImportError(f"coletor fora do teste: {curto}")

    monkeypatch.setattr(importlib, "import_module", importar)
    monkeypatch.setattr(calendario, "mercado_aberto", lambda _agora: True)
    monkeypatch.setattr(agendador, "_avisar_falha", lambda *a, **k: None)
    monkeypatch.setattr(agendador, "_registrar_erro", lambda *a, **k: None)


def _hoje_brt() -> object:
    return datetime.now(timezone.utc).astimezone(agendador.BRT).date()


def test_rodada_le_e_grava_instrumentacao_uma_vez(monkeypatch):
    _isolar_coletores(
        monkeypatch,
        {
            "ibovespa": _coletor(True),
            "mare": _coletor(False),
            "highlights": _coletor(True),
        },
    )
    espiao = _Espiao(monkeypatch)

    agendador._coletar()

    assert espiao.leituras == 1
    assert len(espiao.gravacoes) == 1
    payload = app.banco.ler_snapshot("instrumentacao", _hoje_brt())
    assert set(payload["tempos"]) == {"ibovespa", "mare", "highlights"}
    assert payload["vazias"] == {"mare": 1}
    assert payload["rodadas"] == {"ibovespa": 1, "mare": 1, "highlights": 1}


def test_fusao_do_exemplo_campo_a_campo():
    app.banco.gravar_snapshot("instrumentacao", DIA, "ao_vivo", "sistema", ANTES)

    gravar_instrumentacao_rodada(
        {"ibovespa": 2.0, "mare": 1.5, "highlights": 59.0}, ["mare"], TIMESTAMP
    )

    payload = app.banco.ler_snapshot("instrumentacao", DIA)
    assert payload["tempos"] == DEPOIS["tempos"]
    assert payload["vazias"] == DEPOIS["vazias"]
    assert payload["rodadas"] == DEPOIS["rodadas"]


def test_rodada_sem_medidas_nao_toca_no_banco(monkeypatch):
    espiao = _Espiao(monkeypatch)

    gravar_instrumentacao_rodada({}, [], TIMESTAMP)

    assert espiao.leituras == 0
    assert espiao.gravacoes == []


def test_coletor_que_levanta_nao_impede_a_gravacao(monkeypatch):
    _isolar_coletores(
        monkeypatch,
        {
            "ibovespa": _coletor(True),
            "mare": _coletor(True, falha=True),
            "highlights": _coletor(True),
        },
    )
    espiao = _Espiao(monkeypatch)

    agendador._coletar()

    assert len(espiao.gravacoes) == 1
    tempos = espiao.gravacoes[0]["tempos"]
    assert set(tempos) == {"ibovespa", "highlights"}
    assert "mare" not in espiao.gravacoes[0]["vazias"]


def test_falha_ao_gravar_nao_derruba_a_rodada(monkeypatch):
    _isolar_coletores(monkeypatch, {"ibovespa": _coletor(True)})
    _Espiao(monkeypatch, gravar_falha=True)

    agendador._coletar()  # não pode levantar
