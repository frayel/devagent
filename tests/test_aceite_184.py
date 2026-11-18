"""Aceite da spec 184: os radares de molde único entram no /api/snapshot por um laço.

O JSON publicado não muda. Os 8 getters de `app.database` são trocados por
objetos fixos (sem rede) e a resposta é conferida chave a chave, com dado, sem
dado e com `alertas_json` quebrado.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

import app.database
import app.main
from app.main import app as aplicacao
from devagent.aceite import exigir_spec_done

client = TestClient(aplicacao)

# (chave em `paineis`, getter em `app.database`, forma sem dado)
OITO = [
    ("variacao_subita", "get_latest_variacao_subita_data", "nd"),
    ("faca_caindo", "get_latest_faca_caindo_data", "nd"),
    ("compradores_fundo", "get_latest_compradores_fundo_data", "nd"),
    ("concentracao_ordens", "get_latest_concentracao_ordens_data", "nd"),
    ("armadilha_abertura", "get_latest_armadilha_abertura_data", "nd"),
    ("short_squeeze", "get_latest_radar_short_squeeze_data", "lista"),
    ("radar_inflexao", "get_latest_radar_inflexao_data", "lista"),
    ("radar_absorcao_cruzada", "get_latest_radar_absorcao_cruzada_data", "lista"),
]

COLETA = datetime(2026, 11, 18, 17, 15, tzinfo=timezone.utc)


@dataclass
class _Dado:
    timestamp: datetime
    fonte: str
    alertas_json: str


def _trocar(monkeypatch, valores: dict[str, object]) -> None:
    for _chave, getter, _ in OITO:
        valor = valores.get(getter)
        falso = lambda *a, _v=valor, **k: _v  # noqa: E731
        monkeypatch.setattr(app.database, getter, falso)
        # Antes da spec, parte dos getters vinha de `from app.database import`
        # no topo de app.main; trocar lá também deixa o teste valer contra a
        # main de antes e de depois (depois, o nome não existe mais em app.main).
        if hasattr(app.main, getter):
            monkeypatch.setattr(app.main, getter, falso)


def _dado(ticker: str, fonte: str = "mt5", alertas_json: str | None = None) -> _Dado:
    if alertas_json is None:
        alertas_json = f'[{{"ticker": "{ticker}", "variacao": -2.1}}]'
    return _Dado(timestamp=COLETA, fonte=fonte, alertas_json=alertas_json)


def _paineis() -> dict:
    resposta = client.get("/api/snapshot")
    assert resposta.status_code == 200
    return resposta.json()["paineis"]


def test_com_dado_cada_painel_publica_coleta_fonte_e_alertas(monkeypatch):
    _trocar(monkeypatch, {g: _dado(c.upper()) for c, g, _ in OITO})
    paineis = _paineis()
    for chave, _getter, _ in OITO:
        assert paineis[chave] == {
            "coletado_em": "2026-11-18T17:15:00+00:00",
            "fonte": "mt5",
            "alertas": [{"ticker": chave.upper(), "variacao": -2.1}],
        }, chave


def test_sem_dado_cada_painel_publica_a_forma_de_antes(monkeypatch):
    _trocar(monkeypatch, {})
    resposta = client.get("/api/snapshot")
    assert resposta.status_code == 200
    corpo = resposta.json()
    paineis = corpo["paineis"]
    for chave, _getter, sem_dado in OITO:
        if sem_dado == "nd":
            assert paineis[chave] == {
                "fonte": "nd",
                "coletado_em": corpo["gerado_em"],
            }, chave
        else:
            assert paineis[chave] == [], chave


def test_alertas_json_quebrado_vira_lista_vazia_so_naquele_painel(monkeypatch):
    valores: dict[str, object] = {g: _dado(c.upper()) for c, g, _ in OITO}
    valores["get_latest_compradores_fundo_data"] = _dado(
        "X", fonte="yfinance", alertas_json="{quebrado"
    )
    _trocar(monkeypatch, valores)
    paineis = _paineis()
    assert paineis["compradores_fundo"] == {
        "coletado_em": "2026-11-18T17:15:00+00:00",
        "fonte": "yfinance",
        "alertas": [],
    }
    for chave, _getter, _ in OITO:
        if chave != "compradores_fundo":
            assert paineis[chave]["alertas"] == [
                {"ticker": chave.upper(), "variacao": -2.1}
            ], chave


def test_paineis_sem_dado_nao_compartilham_objeto():
    exigir_spec_done("184")
    agora = datetime(2026, 11, 18, 17, 30, tzinfo=timezone.utc)
    for sem_dado in ("nd", "lista"):
        a = app.main._painel_de_alertas(None, agora, sem_dado)
        b = app.main._painel_de_alertas(None, agora, sem_dado)
        assert a == b
        assert a is not b
    lista = app.main._painel_de_alertas(None, agora, "lista")
    assert lista == []
    nd = app.main._painel_de_alertas(None, agora, "nd")
    assert nd == {"fonte": "nd", "coletado_em": "2026-11-18T17:30:00+00:00"}


def test_painel_de_alertas_segue_o_exemplo_da_spec():
    exigir_spec_done("184")
    agora = datetime(2026, 11, 18, 17, 30, tzinfo=timezone.utc)
    assert app.main._painel_de_alertas(_dado("PETR4"), agora, "nd") == {
        "coletado_em": "2026-11-18T17:15:00+00:00",
        "fonte": "mt5",
        "alertas": [{"ticker": "PETR4", "variacao": -2.1}],
    }
    assert app.main._painel_de_alertas(
        _dado("X", fonte="yfinance", alertas_json="{quebrado"), agora, "lista"
    ) == {
        "coletado_em": "2026-11-18T17:15:00+00:00",
        "fonte": "yfinance",
        "alertas": [],
    }


def test_tabela_declara_os_oito_com_getters_que_existem():
    exigir_spec_done("184")
    tabela = app.main.RADARES_MOLDE_UNICO
    assert sorted(tuple(linha) for linha in tabela) == sorted(OITO)
    for _chave, getter, sem_dado in tabela:
        assert callable(getattr(app.database, getter))
        assert sem_dado in ("nd", "lista")


@pytest.mark.parametrize("getter", [g for _c, g, _ in OITO])
def test_snapshot_nao_chama_os_oito_getters_pelo_nome(getter):
    exigir_spec_done("184")
    assert getter not in inspect.getsource(app.main.snapshot)
