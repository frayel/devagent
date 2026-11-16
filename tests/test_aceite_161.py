"""Aceite da spec 161: "Painéis sem dados" de /sistema conta só a janela que anuncia.

`gravar_instrumentacao_rodada` passa a somar as contagens por hora BRT em
`por_hora`, e `get_coletas_vazias_desde`/`get_rodadas_coleta_desde` somam só as
horas cheias que começam em `desde` ou depois. Sem rede e sem depender da hora
real: o banco é o SQLite temporário do conftest e `agora` é passado sempre.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest

import app.banco
from app.calendario import BRT
from app.database import (
    get_coletas_vazias_desde,
    get_rodadas_coleta_desde,
    gravar_instrumentacao_rodada,
)
from app.services import sistema as s
from devagent.aceite import exigir_spec_done

DIA = date(2026, 11, 16)


@pytest.fixture(autouse=True)
def _spec_done():
    exigir_spec_done("161")


def _brt(dia: date, hora: int, minuto: int = 0, segundo: int = 0) -> datetime:
    return datetime(dia.year, dia.month, dia.day, hora, minuto, segundo, tzinfo=BRT)


def _rodadas_do_exemplo(ate: datetime, quebra_as_14h: bool = False) -> None:
    """Rodadas a cada 15 min das 10h00 até `ate`; `mare` vazio nas 4 primeiras."""
    t = _brt(DIA, 10)
    i = 0
    while t <= ate:
        vazio = i < 4 or (quebra_as_14h and t >= _brt(DIA, 14))
        gravar_instrumentacao_rodada(
            {"mare": 1.0, "ibovespa": 2.0}, ["mare"] if vazio else [], t
        )
        t += timedelta(minutes=15)
        i += 1


def test_por_hora_do_exemplo_e_contagens_do_dia():
    _rodadas_do_exemplo(_brt(DIA, 17))
    payload = app.banco.ler_snapshot("instrumentacao", DIA)

    cheia = {"rodadas": {"mare": 4, "ibovespa": 4}, "vazias": {}}
    esperado = {
        "10": {"rodadas": {"mare": 4, "ibovespa": 4}, "vazias": {"mare": 4}},
        **{f"{h:02d}": cheia for h in range(11, 17)},
        "17": {"rodadas": {"mare": 1, "ibovespa": 1}, "vazias": {}},
    }
    assert payload["por_hora"] == esperado
    assert payload["rodadas"] == {"mare": 29, "ibovespa": 29}
    assert payload["vazias"] == {"mare": 4}


def test_janela_de_3h_as_17h05_ignora_os_vazios_da_manha():
    _rodadas_do_exemplo(_brt(DIA, 17))
    agora = _brt(DIA, 17, 5)
    desde = _brt(DIA, 14, 5)

    assert get_coletas_vazias_desde(desde, agora=agora) == {}
    assert get_rodadas_coleta_desde(desde, agora=agora) == {"mare": 9, "ibovespa": 9}


def test_janela_as_11h05_conta_os_vazios_da_manha():
    _rodadas_do_exemplo(_brt(DIA, 11))
    agora = _brt(DIA, 11, 5)
    desde = _brt(DIA, 8, 5)

    vazios = get_coletas_vazias_desde(desde, agora=agora)
    rodadas = get_rodadas_coleta_desde(desde, agora=agora)
    assert vazios == {"mare": 4}
    assert rodadas == {"mare": 5, "ibovespa": 5}

    item = s.verificar_paineis_vazios(vazios, 3, rodadas)
    assert item.nivel == s.ATENCAO
    assert "1 painel vazio nas últimas 3 h" in item.resumo


def test_desde_na_hora_cheia_conta_a_hora_e_um_segundo_depois_nao():
    _rodadas_do_exemplo(_brt(DIA, 17))
    agora = _brt(DIA, 17, 5)

    assert get_rodadas_coleta_desde(_brt(DIA, 15), agora=agora) == {
        "mare": 9,
        "ibovespa": 9,
    }
    assert get_rodadas_coleta_desde(_brt(DIA, 15, 0, 1), agora=agora) == {
        "mare": 5,
        "ibovespa": 5,
    }


def test_coletor_quebrado_vira_problema():
    _rodadas_do_exemplo(_brt(DIA, 17), quebra_as_14h=True)
    agora = _brt(DIA, 17, 5)
    desde = _brt(DIA, 14, 5)

    vazios = get_coletas_vazias_desde(desde, agora=agora)
    rodadas = get_rodadas_coleta_desde(desde, agora=agora)
    assert vazios == {"mare": 9}
    assert rodadas["mare"] == 9

    item = s.verificar_paineis_vazios(vazios, 3, rodadas)
    assert item.nivel == s.PROBLEMA
    assert "1 sempre vazio: mare" in item.resumo


def test_virada_do_dia_le_as_duas_datas():
    amanha = DIA + timedelta(days=1)
    for t in (_brt(DIA, 23), _brt(amanha, 1)):
        gravar_instrumentacao_rodada({"mare": 1.0, "ibovespa": 2.0}, ["mare"], t)
    agora = _brt(amanha, 1, 10)
    desde = _brt(DIA, 22, 10)

    vazios = get_coletas_vazias_desde(desde, agora=agora)
    rodadas = get_rodadas_coleta_desde(desde, agora=agora)
    assert vazios == {"mare": 2}
    assert rodadas == {"mare": 2, "ibovespa": 2}
    assert s.verificar_paineis_vazios(vazios, 3, rodadas).nivel == s.ATENCAO


def test_snapshot_sem_por_hora_nao_contribui():
    app.banco.gravar_snapshot(
        "instrumentacao",
        DIA,
        "ao_vivo",
        "sistema",
        {"tempos": {"mare": 1.0}, "rodadas": {"mare": 29}, "vazias": {"mare": 4}},
    )
    agora = _brt(DIA, 17, 5)
    desde = _brt(DIA, 8, 5)

    assert get_coletas_vazias_desde(desde, agora=agora) == {}
    assert get_rodadas_coleta_desde(desde, agora=agora) == {}


def test_gravacao_continua_com_uma_leitura_e_uma_gravacao(monkeypatch):
    leituras = 0
    gravacoes = 0
    ler_original = app.banco.ler_snapshot
    gravar_original = app.banco.gravar_snapshot

    def ler(painel, data_referencia=None):
        nonlocal leituras
        if painel == "instrumentacao":
            leituras += 1
        return ler_original(painel, data_referencia)

    def gravar(painel, *args, **kwargs):
        nonlocal gravacoes
        if painel == "instrumentacao":
            gravacoes += 1
        return gravar_original(painel, *args, **kwargs)

    monkeypatch.setattr(app.banco, "ler_snapshot", ler)
    monkeypatch.setattr(app.banco, "gravar_snapshot", gravar)

    gravar_instrumentacao_rodada(
        {"mare": 1.0, "ibovespa": 2.0}, ["mare"], _brt(DIA, 10)
    )
    assert (leituras, gravacoes) == (1, 1)

    gravar_instrumentacao_rodada({}, [], _brt(DIA, 10, 15))
    assert (leituras, gravacoes) == (1, 1)
