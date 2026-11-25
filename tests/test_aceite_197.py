"""Aceite da spec 197: as frases do Consultor escrevem números no padrão brasileiro.

Sem rede: as regras, o placar e a confiança são funções puras; a página é montada
com um dublê de `calcular_consultor`, no molde de `tests/test_aceite_191.py`.
"""

from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient

import app.main
from app.consultor.calculador import confianca_da_regra
from app.consultor.placar import _mensagem_do_placar
from app.consultor.regras import avaliar_ativo
from app.consultor.sintese import obter_decisao_final
from app.main import app as fastapi_app
from devagent.aceite import exigir_spec_done

# Ponto como separador decimal (`45.68`, `1.5`); o ponto de milhar (`1.275,75`)
# é justamente o padrão brasileiro e não conta.
PONTO_DECIMAL = re.compile(r"\d\.(?!\d{3}(?:\D|$))\d")
REAIS_BR = re.compile(r"R\$ \d{1,3}(\.\d{3})+,\d{2}")
IBOV = [100000.0] * 250
VOLUMES = [1.0] * 250


@pytest.fixture(autouse=True)
def _so_com_spec_done():
    exigir_spec_done("197")


def _zigue(inicio, passo, amplitude, n=250):
    return [inicio + passo * i + (amplitude if i % 2 else -amplitude) for i in range(n)]


SERIES = {
    "R2 Tendência de baixa": _zigue(1500, -1.5, 8),
    "R3 Esticada": [1000.0] * 220 + [1000 + 15 * i for i in range(1, 31)],
    "R4 Rompimento pendente": [1240.0] * 215
    + [1200.0] * 15
    + [1200 + 1.0 * i for i in range(1, 21)],
    "R5 Tendência de alta saudável": _zigue(1000, 1.0, 6),
}


@pytest.mark.parametrize("regra", list(SERIES))
def test_regras_com_mm200_acima_de_mil(regra):
    avaliacao = avaliar_ativo("TESTE3", SERIES[regra], VOLUMES, IBOV)
    assert avaliacao["regra"] == regra
    assert avaliacao["mm200"] > 1000
    assert REAIS_BR.search(avaliacao["gatilho"]), avaliacao["gatilho"]
    assert not PONTO_DECIMAL.search(avaliacao["gatilho"]), avaliacao["gatilho"]
    assert not PONTO_DECIMAL.search(avaliacao["motivo"]), avaliacao["motivo"]


def test_r2_mostra_o_preco_da_mm200_por_extenso():
    avaliacao = avaliar_ativo("TESTE3", SERIES["R2 Tendência de baixa"], VOLUMES, IBOV)
    assert avaliacao["gatilho"] == "Fechamento acima da MM200 (R$ 1.275,75)"
    assert avaliacao["motivo"].startswith(
        "Preço < MM200 (1.275,75), MM21 < MM200, FR20 (-"
    )


def test_r4_termina_com_vol_rel_brasileiro():
    avaliacao = avaliar_ativo("TESTE3", SERIES["R4 Rompimento pendente"], VOLUMES, IBOV)
    assert avaliacao["gatilho"].endswith("com VOL_REL >= 1,0")


def test_r1_termina_com_vol_rel_brasileiro():
    closes = [1500.0 - i for i in range(250)]
    avaliacao = avaliar_ativo("TESTE3", closes, VOLUMES, IBOV)
    assert avaliacao["regra"] == "R1 Faca caindo"
    assert avaliacao["gatilho"].endswith("VOL_REL >= 1,5")


def test_gatilhos_da_sintese():
    vender = obter_decisao_final(
        {"decisao": "Vender", "gatilho": "g", "mm200": 1234.5},
        {"consenso": "compra", "detalhes": {"total": 3}},
        1200.0,
        1210.0,
    )
    assert vender[2] == "Fechamento acima da MM200 (R$ 1.234,50)"

    radar = obter_decisao_final(
        {"decisao": "Sem sinal", "gatilho": "-", "mm200": 1.0},
        {"consenso": "compra", "detalhes": {"total": 3}, "potencial": 0.2},
        1200.0,
        1234.5,
    )
    assert radar[0] == "No radar"
    assert radar[2] == "fechamento acima da MM21 (R$ 1.234,50)"

    sem_mm200 = obter_decisao_final(
        {"decisao": "Vender", "gatilho": "g"},
        {"consenso": "compra", "detalhes": {"total": 3}},
        1200.0,
        None,
    )
    assert sem_mm200[2] == "Fechamento acima da MM200 (-)"


def _placar(offset_disponivel, preco_futuro, ibov_futuro):
    pregoes = [f"2023-11-0{i}" for i in range(1, 2 + offset_disponivel)]
    futuro = pregoes[-1]
    fechamentos = {
        (futuro, "TESTE3"): preco_futuro,
        ("2023-11-01", "^BVSP"): 120000.0,
        (futuro, "^BVSP"): ibov_futuro,
    }
    recomendacao = {
        "timestamp": "2023-11-01 18:00:00 BRT",
        "ticker": "TESTE3",
        "preco": 30.0,
    }
    return _mensagem_do_placar(recomendacao, pregoes, fechamentos)


def test_placar_no_padrao_brasileiro():
    assert _placar(5, 33.0, 126000.0) == "+5,0% contra o IBOV em 5 pregões"
    assert _placar(1, 33.0, 126000.0) == "+5,0% contra o IBOV em 1 pregão"
    # Ativo -2,3% e IBOV parado: excesso -0,023.
    assert _placar(5, 30.0 * (1 - 0.023), 120000.0).startswith("-2,3%")


def test_confianca_no_padrao_brasileiro():
    historico = {
        "R5 Teste": {"disparos": 120, "acertos": 75, "excesso_mediano": 0.0321}
    }
    mensagem = confianca_da_regra("R5 Teste", historico)["mensagem"]
    assert mensagem.endswith("(mediana +3,2 p.p.).")

    historico["R5 Teste"]["excesso_mediano"] = -0.004
    assert confianca_da_regra("R5 Teste", historico)["mensagem"].endswith(
        "(mediana -0,4 p.p.)."
    )
    historico["R5 Teste"]["excesso_mediano"] = 0.0
    assert confianca_da_regra("R5 Teste", historico)["mensagem"].endswith(
        "(mediana +0,0 p.p.)."
    )


def test_tabela_de_regras_na_pagina(monkeypatch):
    monkeypatch.delenv("CONSULTOR_SENHA", raising=False)

    def mock_calc():
        return {
            "resultados": {
                "Comprar": [],
                "Vender": [],
                "Aguardar": [],
                "No radar": [],
                "Sem sinal": [],
            },
            "opinioes_recentes": [],
            "opinioes_por_ativo": [],
            "opinioes_status": {
                "status": "ok",
                "motivo": "",
                "desde": "",
                "ultima_extracao_em": "2026-11-21T10:00:00+00:00",
                "materias_processadas": 0,
                "opinioes_gravadas": 0,
                "descartadas": 0,
            },
            "ativos_avaliados": 0,
        }

    monkeypatch.setattr(app.main, "calcular_consultor", mock_calc)
    resposta = TestClient(fastapi_app).get("/consultor")
    assert resposta.status_code == 200
    html = resposta.text
    assert "VOL_REL >= 1.5" not in html
    assert "VOL_REL >= 1.0" not in html
    assert "VOL_REL >= 1,5" in html
    assert "VOL_REL >= 1,0" in html
