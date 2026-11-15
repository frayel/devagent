"""Aceite da spec 154: o critério de poda conta só as coletas do pregão.

A rodada que começa com o mercado aberto soma também em `rodadas_pregao` e
`vazias_pregao`; `verificar_candidatos_poda` lê só essas chaves. Sem rede: o
banco é o SQLite temporário do conftest e os coletores são falsos.
"""

from __future__ import annotations

import importlib
from datetime import date, datetime, timezone

import pytest

import app.banco
import app.database
from app import agendador
from app.database import gravar_instrumentacao_rodada
from app.services import sistema as s
from devagent.aceite import exigir_spec_done

DIA = date(2026, 11, 16)
# 10h15 e 18h45 BRT (UTC-3) de segunda, 16/11/2026.
PREGAO = datetime(2026, 11, 16, 13, 15, tzinfo=timezone.utc)
DEPOIS_DO_FECHAMENTO = datetime(2026, 11, 16, 21, 45, tzinfo=timezone.utc)

ANTES = {
    "tempos": {"mare": 1.0},
    "rodadas": {"mare": 3},
    "vazias": {"mare": 1},
    "rodadas_pregao": {"mare": 2},
    "vazias_pregao": {"mare": 1},
}

PREGOES = [
    date(2026, 11, 13),
    date(2026, 11, 12),
    date(2026, 11, 11),
    date(2026, 11, 10),
    date(2026, 11, 9),
    date(2026, 11, 6),
    date(2026, 11, 5),
    date(2026, 11, 4),
    date(2026, 11, 3),
    date(2026, 10, 30),
]
PAYLOAD_DIA = {
    "rodadas": {"fator_peso_pesado": 34, "atrasadas_rally": 34},
    "vazias": {"fator_peso_pesado": 18, "atrasadas_rally": 17},
    "rodadas_pregao": {"fator_peso_pesado": 30, "atrasadas_rally": 30},
    "vazias_pregao": {"fator_peso_pesado": 14, "atrasadas_rally": 16},
}


@pytest.fixture(autouse=True)
def _spec_done():
    exigir_spec_done("154")


def test_gravacao_do_exemplo_campo_a_campo():
    app.banco.gravar_snapshot("instrumentacao", DIA, "ao_vivo", "sistema", ANTES)

    gravar_instrumentacao_rodada(
        {"mare": 1.5, "ibovespa": 2.0}, ["mare"], PREGAO, durante_pregao=True
    )
    payload = app.banco.ler_snapshot("instrumentacao", DIA)
    assert payload["tempos"] == {"mare": 1.5, "ibovespa": 2.0}
    assert payload["rodadas"] == {"mare": 4, "ibovespa": 1}
    assert payload["vazias"] == {"mare": 2}
    assert payload["rodadas_pregao"] == {"mare": 3, "ibovespa": 1}
    assert payload["vazias_pregao"] == {"mare": 2}

    gravar_instrumentacao_rodada(
        {"mare": 0.8}, ["mare"], DEPOIS_DO_FECHAMENTO, durante_pregao=False
    )
    payload = app.banco.ler_snapshot("instrumentacao", DIA)
    assert payload["tempos"] == {"mare": 0.8, "ibovespa": 2.0}
    assert payload["rodadas"] == {"mare": 5, "ibovespa": 1}
    assert payload["vazias"] == {"mare": 3}
    assert payload["rodadas_pregao"] == {"mare": 3, "ibovespa": 1}
    assert payload["vazias_pregao"] == {"mare": 2}


def test_fora_do_pregao_nao_cria_a_chave():
    gravar_instrumentacao_rodada({"mare": 0.8}, ["mare"], DEPOIS_DO_FECHAMENTO)
    payload = app.banco.ler_snapshot("instrumentacao", DIA)
    assert payload["rodadas"] == {"mare": 1}
    assert "rodadas_pregao" not in payload
    assert "vazias_pregao" not in payload


def _relogio(instante: datetime) -> type[datetime]:
    class _Relogio(datetime):
        @classmethod
        def now(cls, tz=None):  # type: ignore[override]
            return instante if tz is None else instante.astimezone(tz)

    return _Relogio


def _coletor(ok: bool):
    class _Coletor:
        @staticmethod
        def collect_and_save():
            return ok

    return _Coletor


@pytest.mark.parametrize(
    ("instante", "esperado"), [(PREGAO, True), (DEPOIS_DO_FECHAMENTO, False)]
)
def test_coletar_passa_o_relogio_do_inicio_da_rodada(monkeypatch, instante, esperado):
    coletores = {"ibovespa": _coletor(True), "mare": _coletor(False)}

    def importar(nome):
        curto = nome.rsplit(".", 1)[-1]
        if curto in coletores:
            return coletores[curto]
        raise ImportError(f"coletor fora do teste: {curto}")

    chamadas: list[dict] = []

    def espiar(tempos, vazias, timestamp, durante_pregao=False):
        chamadas.append({"durante_pregao": durante_pregao})

    monkeypatch.setattr(importlib, "import_module", importar)
    monkeypatch.setattr(agendador, "datetime", _relogio(instante))
    monkeypatch.setattr(agendador, "_avisar_falha", lambda *a, **k: None)
    monkeypatch.setattr(agendador, "_registrar_erro", lambda *a, **k: None)
    monkeypatch.setattr(app.database, "gravar_instrumentacao_rodada", espiar)

    agendador._coletar()

    assert chamadas == [{"durante_pregao": esperado}]


def test_criterio_conta_so_o_pregao():
    historico = {d: PAYLOAD_DIA for d in PREGOES}
    item = s.verificar_candidatos_poda(historico, PREGOES)
    assert item.nivel == "atencao"
    assert item.resumo == (
        "1 painel vazio em mais da metade das coletas dos últimos 10 pregões"
    )
    assert item.detalhe == "atrasadas_rally (160 de 300, 53%)"
    assert "fator_peso_pesado" not in item.detalhe


def test_snapshot_antigo_conta_como_ausente():
    historico = {d: PAYLOAD_DIA for d in PREGOES}
    historico[date(2026, 10, 30)] = {
        "rodadas": PAYLOAD_DIA["rodadas"],
        "vazias": PAYLOAD_DIA["vazias"],
    }
    item = s.verificar_candidatos_poda(historico, PREGOES)
    assert item.nivel == "ok"
    assert item.resumo == "histórico de 9 de 10 pregões; o critério precisa de 10"
