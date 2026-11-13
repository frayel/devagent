"""Aceite da spec 142: a lista de ganhos não repete a pressão vendedora."""

from __future__ import annotations

import json
import re

import respx

from app.collectors.concentracao import (
    TICKERS_PESOS,
    fetch_concentracao_vendedora_yfinance,
    fetch_yfinance,
)
from devagent.aceite import exigir_spec_done

SPARK = re.compile(r"https://query[12]\.finance\.yahoo\.com/v8/finance/spark.*")
IBOV_PREV = 100_000.0


def test_aceite_142_spec_done():
    exigir_spec_done("142")


def _serie(simbolo: str, prev: float, atual: float) -> dict:
    return {
        "symbol": simbolo,
        "response": [{"indicators": {"quote": [{"close": [prev, atual]}]}}],
    }


def _resposta(ibov_atual: float, pontos: dict[str, float]) -> dict:
    """Monta o `spark` para que cada ticker renda os pontos teóricos pedidos.

    pontos = var × peso × IBOV_PREV, logo var = pontos / (peso × IBOV_PREV).
    """
    result = [_serie("^BVSP", IBOV_PREV, ibov_atual)]
    for ticker, pts in pontos.items():
        var = pts / (TICKERS_PESOS[ticker] * IBOV_PREV)
        result.append(_serie(f"{ticker}.SA", 100.0, 100.0 * (1 + var)))
    return {"spark": {"result": result}}


def _coletar(ibov_atual: float, pontos: dict[str, float]):
    with respx.mock:
        respx.get(SPARK).respond(json=_resposta(ibov_atual, pontos))
        return fetch_yfinance(), fetch_concentracao_vendedora_yfinance()


# Índice −919: três perdedores (WEGE3, PETR4, BBDC4) e quatro ganhadores
# de 100 pontos cada (sete no total): metade dos ganhos pede quatro nomes.
QUEDA = {
    "WEGE3": -500.0,
    "PETR4": -400.0,
    "BBDC4": -300.0,
    "VALE3": 100.0,
    "ITUB4": 100.0,
    "PETR3": 100.0,
    "B3SA3": 100.0,
    "ABEV3": 100.0,
    "BBDC3": 100.0,
    "BBAS3": 100.0,
}


def _linhas(dado) -> list[dict]:
    return json.loads(dado.top3_json)


def _mensagem(dado) -> str:
    return json.loads(dado.resumo_json)["mensagem"]


def test_listas_separadas_por_sinal():
    ganhos, pressao = _coletar(IBOV_PREV - 919, QUEDA)
    assert all(a["pontos"] > 0 for a in _linhas(ganhos))
    assert all(a["pontos"] < 0 for a in _linhas(pressao))
    nomes_ganhos = {a["ticker"] for a in _linhas(ganhos)}
    assert not nomes_ganhos & {"WEGE3", "PETR4", "BBDC4"}
    # A pressão usa o corte de 50%: 500 + 400 ≥ 600.
    assert [a["ticker"] for a in _linhas(pressao)] == ["WEGE3", "PETR4"]


def test_n_da_frase_igual_as_linhas():
    # Sete ganhadores de 100: metade de 700 pede 4 nomes.
    ganhos, pressao = _coletar(IBOV_PREV - 919, QUEDA)
    assert len(_linhas(ganhos)) == 4
    assert re.search(r"\b4 ações\b", _mensagem(ganhos))
    assert len(_linhas(pressao)) == 2
    assert re.search(r"\b2 ações\b", _mensagem(pressao))


def test_frase_de_ganhos_em_queda_fala_em_compensar():
    ganhos, _ = _coletar(IBOV_PREV - 919, QUEDA)
    texto = _mensagem(ganhos)
    assert "compens" in texto
    assert "pontos de queda" not in texto


def test_parcela_acima_de_100_nao_e_cortada():
    # Índice +500; um único ganhador de 700 pontos = 140% do movimento.
    ganhos, _ = _coletar(IBOV_PREV + 500, {"VALE3": 700.0, "PETR4": -200.0})
    texto = _mensagem(ganhos)
    assert "140%" in texto
    assert "100%" not in texto
    assert "compens" in texto


def test_ticker_sem_barra_reduz_k():
    pontos = dict(QUEDA)
    pontos.pop("BBAS3")
    ganhos, pressao = _coletar(IBOV_PREV - 919, pontos)
    assert "9 de 10 da cesta" in _mensagem(ganhos)
    assert "9 de 10 da cesta" in _mensagem(pressao)


def test_pressao_com_indice_em_alta_publica_lista_negativa():
    _, pressao = _coletar(IBOV_PREV + 800, {"VALE3": 900.0, "PETR4": -300.0})
    assert pressao is not None
    assert [a["ticker"] for a in _linhas(pressao)] == ["PETR4"]
    assert "segur" in _mensagem(pressao)


def test_ganhos_sem_positivo_nao_copia_perdedores():
    ganhos, _ = _coletar(IBOV_PREV - 919, {"WEGE3": -500.0, "PETR4": -400.0})
    resumo = json.loads(ganhos.resumo_json)
    assert resumo["estado"] == "vazio"
    assert "Nenhuma contribuição positiva" in resumo["mensagem"]
    assert _linhas(ganhos) == []


def test_indice_estavel_nos_dois_cards():
    ganhos, pressao = _coletar(IBOV_PREV + 50, {"VALE3": 100.0, "PETR4": -100.0})
    for dado in (ganhos, pressao):
        resumo = json.loads(dado.resumo_json)
        assert resumo["estado"] == "estavel"
        assert resumo["mensagem"] == "Ibovespa estável, sem concentração definida."
        assert _linhas(dado) == []
