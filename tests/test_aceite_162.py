"""Aceite da spec 162: a "Duração da coleta" de /sistema é a da última rodada.

`_coletar` mede a rodada inteira no relógio e `gravar_instrumentacao_rodada`
guarda `ultima_rodada` no snapshot `instrumentacao` do dia; `get_ultima_rodada`
lê o dia e a véspera numa só consulta e o item mostra essa rodada. Sem rede e
sem hora real: o banco é o SQLite temporário do conftest e `agora` é explícito.
"""

from __future__ import annotations

import importlib
from datetime import date, datetime, timezone

import pytest

import app.banco
from app import agendador, calendario
from app.database import get_ultima_rodada, gravar_instrumentacao_rodada
from app.services import sistema as s
from devagent.aceite import exigir_spec_done

DIA = date(2026, 11, 16)
DIA_17 = date(2026, 11, 17)

TEMPOS_18H15 = {
    "ibovespa": 2.0,
    "mare": 1.5,
    "highlights": 59.0,
    "consultor_yahoo": 240.0,
    "consultor_opinioes": 30.0,
}
INICIO = datetime(2026, 11, 16, 22, 0, tzinfo=timezone.utc)
FIM = datetime(2026, 11, 16, 22, 4, 51, 400000, tzinfo=timezone.utc)
ULTIMA_RODADA = {
    "inicio": "2026-11-16T22:00:00+00:00",
    "fim": "2026-11-16T22:04:51.400000+00:00",
    "duracao_parede": 291.4,
    "tempos": {"consultor_yahoo": 250.0, "consultor_opinioes": 35.0},
}
# 19h10 BRT de 16/11/2026.
AGORA_19H10 = datetime(2026, 11, 16, 22, 10, tzinfo=timezone.utc)
# 0h30 BRT de 17/11/2026.
AGORA_0H30 = datetime(2026, 11, 17, 3, 30, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def _spec_done():
    exigir_spec_done("162")


def _item(rodada):
    return s.verificar_tempo_coleta(
        rodada["tempos"],
        rodada["duracao_parede"],
        datetime.fromisoformat(rodada["inicio"]),
        datetime.fromisoformat(rodada["fim"]),
    )


def _gravar_exemplo():
    app.banco.gravar_snapshot(
        "instrumentacao", DIA, "ao_vivo", "sistema", {"tempos": dict(TEMPOS_18H15)}
    )
    gravar_instrumentacao_rodada(
        {"consultor_yahoo": 250.0, "consultor_opinioes": 35.0},
        [],
        FIM,
        durante_pregao=False,
        inicio=INICIO,
        duracao_parede=291.4,
    )


def test_gravacao_do_exemplo():
    _gravar_exemplo()

    payload = app.banco.ler_snapshot("instrumentacao", DIA)
    assert payload["ultima_rodada"] == ULTIMA_RODADA
    assert payload["tempos"] == {
        "ibovespa": 2.0,
        "mare": 1.5,
        "highlights": 59.0,
        "consultor_yahoo": 250.0,
        "consultor_opinioes": 35.0,
    }


def test_item_mostra_a_rodada_das_19h():
    _gravar_exemplo()

    rodada = get_ultima_rodada(agora=AGORA_19H10)
    assert rodada == ULTIMA_RODADA
    item = _item(rodada)
    assert item.resumo == "rodada das 19h00 em 4,9 min"
    assert item.detalhe == "Mais lentos: consultor_yahoo 250 s, consultor_opinioes 35 s"
    assert item.nivel == s.OK
    assert item.quando == ULTIMA_RODADA["fim"]


def test_virada_do_dia_le_as_duas_datas_numa_consulta(monkeypatch):
    rodada_23h = {
        "inicio": "2026-11-17T02:00:00+00:00",
        "fim": "2026-11-17T02:00:40+00:00",
        "duracao_parede": 40.0,
        "tempos": {"consultor_opinioes": 38.0},
    }
    app.banco.gravar_snapshot(
        "instrumentacao", DIA, "ao_vivo", "sistema", {"ultima_rodada": rodada_23h}
    )
    chamadas: list[list[date]] = []
    original = app.banco.ler_snapshots_datas

    def espiar(painel, datas):
        chamadas.append(list(datas))
        return original(painel, datas)

    monkeypatch.setattr(app.banco, "ler_snapshots_datas", espiar)

    rodada = get_ultima_rodada(agora=AGORA_0H30)

    assert rodada == rodada_23h
    assert len(chamadas) == 1
    assert set(chamadas[0]) == {DIA, DIA_17}
    assert _item(rodada).resumo == "rodada das 23h00 em 0,7 min"


def test_vence_a_rodada_de_maior_fim():
    da_vespera = {
        "inicio": "2026-11-17T02:00:00+00:00",
        "fim": "2026-11-17T02:00:40+00:00",
        "duracao_parede": 40.0,
        "tempos": {"mare": 1.0},
    }
    de_hoje = {
        "inicio": "2026-11-17T03:05:00+00:00",
        "fim": "2026-11-17T03:06:00+00:00",
        "duracao_parede": 60.0,
        "tempos": {"mare": 2.0},
    }
    app.banco.gravar_snapshot(
        "instrumentacao", DIA, "ao_vivo", "sistema", {"ultima_rodada": da_vespera}
    )
    app.banco.gravar_snapshot(
        "instrumentacao", DIA_17, "ao_vivo", "sistema", {"ultima_rodada": de_hoje}
    )

    assert get_ultima_rodada(agora=AGORA_0H30) == de_hoje


def test_snapshot_antigo_sem_ultima_rodada_fica_sem_medicoes():
    for dia in (DIA, DIA_17):
        app.banco.gravar_snapshot(
            "instrumentacao", dia, "ao_vivo", "sistema", {"tempos": {"mare": 1.0}}
        )

    rodada = get_ultima_rodada(agora=AGORA_0H30)

    assert rodada is None
    item = s.verificar_tempo_coleta({})
    assert item.nivel == s.INATIVO
    assert item.resumo == "sem medições"


def test_lentidao_real_vira_atencao():
    tempos = {"highlights": 300.0, "consultor_yahoo": 290.0}
    item = s.verificar_tempo_coleta(tempos, 615.0, INICIO, FIM)
    assert item.nivel == s.ATENCAO
    assert "10,2 min" in item.resumo


def test_sem_argumentos_novos_nao_toca_em_ultima_rodada():
    _gravar_exemplo()

    gravar_instrumentacao_rodada({"mare": 0.8}, [], FIM)

    payload = app.banco.ler_snapshot("instrumentacao", DIA)
    assert payload["ultima_rodada"] == ULTIMA_RODADA
    assert payload["tempos"]["mare"] == 0.8


def test_tempos_vazio_nao_toca_no_banco(monkeypatch):
    chamadas: list[str] = []
    monkeypatch.setattr(
        app.banco, "ler_snapshot", lambda *a, **k: chamadas.append("ler")
    )
    monkeypatch.setattr(
        app.banco, "gravar_snapshot", lambda *a, **k: chamadas.append("gravar")
    )

    gravar_instrumentacao_rodada({}, [], FIM, inicio=INICIO, duracao_parede=10.0)

    assert chamadas == []


def test_montar_sem_rodada_mantem_o_resumo_de_hoje():
    item = s.verificar_tempo_coleta({"mare": 12.0})
    assert item.resumo == "rodada completa em 0,2 min"


def _coletor(ok: bool):
    class _Coletor:
        @staticmethod
        def collect_and_save():
            return ok

    return _Coletor


def test_coletar_grava_a_rodada_inteira(monkeypatch):
    coletores = {"ibovespa": _coletor(True), "mare": _coletor(False)}

    def importar(nome):
        curto = nome.rsplit(".", 1)[-1]
        if curto in coletores:
            return coletores[curto]
        raise ImportError(f"coletor fora do teste: {curto}")

    leituras = 0
    gravacoes: list[dict] = []
    ler_original = app.banco.ler_snapshot
    gravar_original = app.banco.gravar_snapshot

    def ler(painel, data_referencia=None):
        nonlocal leituras
        if painel == "instrumentacao":
            leituras += 1
        return ler_original(painel, data_referencia)

    def gravar(painel, *args, **kwargs):
        if painel == "instrumentacao":
            gravacoes.append(args[-1])
        return gravar_original(painel, *args, **kwargs)

    monkeypatch.setattr(importlib, "import_module", importar)
    monkeypatch.setattr(calendario, "mercado_aberto", lambda _agora: True)
    monkeypatch.setattr(agendador, "_avisar_falha", lambda *a, **k: None)
    monkeypatch.setattr(agendador, "_registrar_erro", lambda *a, **k: None)
    monkeypatch.setattr(app.banco, "ler_snapshot", ler)
    monkeypatch.setattr(app.banco, "gravar_snapshot", gravar)

    agendador._coletar()

    assert leituras == 1
    assert len(gravacoes) == 1
    rodada = gravacoes[0]["ultima_rodada"]
    assert set(rodada["tempos"]) == {"ibovespa", "mare"}
    assert rodada["duracao_parede"] >= sum(rodada["tempos"].values())
    assert datetime.fromisoformat(rodada["inicio"]) <= datetime.fromisoformat(
        rodada["fim"]
    )
