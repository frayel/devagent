"""Aceite da spec 177: a Calma não apaga o pânico de verdade.

Sem rede: séries sintéticas do Ibovespa e de uma cesta de 25 ações, com uma
queda de 14% no pregão `t` (como em 26/10/2026).
"""

from __future__ import annotations

import math
import random
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.collectors import mare_historico
from app.services import mare
from devagent.aceite import exigir_spec_done


@pytest.fixture(autouse=True)
def _spec_done():
    exigir_spec_done("177")


N_DIAS = 300
QUEDA_IBOV = 0.86  # −14% no pregão t
POS_T = N_DIAS - 15  # t fica dentro da janela de Ondas, com 9 pregões depois


def _pregoes(n: int) -> list[date]:
    dias, d = [], date(2025, 6, 2)
    while len(dias) < n:
        if d.weekday() < 5:
            dias.append(d)
        d += timedelta(days=1)
    return dias


DIAS = _pregoes(N_DIAS)
T = DIAS[POS_T]


def _ibov() -> dict[date, float]:
    rnd = random.Random(177)
    nivel, serie = 150_000.0, {}
    for i, d in enumerate(DIAS):
        if i:
            nivel *= QUEDA_IBOV if i == POS_T else 1 + rnd.uniform(-0.01, 0.01)
        serie[d] = nivel
    return serie


def _cesta(
    variacao_t: float, n_acoes: int = 25, sem_t: int = 0
) -> dict[str, mare.SerieAcao]:
    """Cesta em que todas as ações variam `variacao_t` no pregão t (a mediana).

    As `sem_t` primeiras ações não têm o pregão t.
    """
    rnd = random.Random(1770)
    cesta: dict[str, mare.SerieAcao] = {}
    for k in range(n_acoes):
        preco, serie = 30.0 + k, {}
        for i, d in enumerate(DIAS):
            if i:
                preco *= (
                    1 + variacao_t if i == POS_T else 1 + rnd.uniform(-0.015, 0.015)
                )
            if i == POS_T and k < sem_t:
                continue
            serie[d] = (preco, 1_000_000.0 + rnd.uniform(-1e5, 1e5))
        cesta[f"ACAO{k}3"] = serie
    return cesta


def _confirmacao(variacao_t: float) -> list[float | None]:
    return [math.log(1 + variacao_t) if i == POS_T else None for i in range(N_DIAS)]


def _fechamentos() -> list[float]:
    ibov = _ibov()
    return [ibov[d] for d in DIAS]


def _volatilidades_de_18_11(fechamentos: list[float]) -> list[float | None]:
    """A função como estava na main de 18/11/2026, para a comparação exata."""
    retornos: list[float | None] = [None]
    for anterior, atual in zip(fechamentos, fechamentos[1:]):
        if anterior > 0 and atual > 0:
            r = math.log(atual / anterior)
            retornos.append(r if abs(r) < 0.12 else None)
        else:
            retornos.append(None)
    saida: list[float | None] = []
    for i in range(len(fechamentos)):
        trecho = retornos[i - 10 + 1 : i + 1] if i >= 1 else []
        janela = [r for r in trecho if r is not None]
        if i < 10 or len(janela) < 10:
            saida.append(None)
            continue
        quedas = [min(r, 0.0) ** 2 for r in janela]
        saida.append(math.sqrt(sum(quedas) / len(quedas)) * math.sqrt(252))
    return saida


# --- volatilidades com a confirmação -----------------------------------------


def test_queda_confirmada_entra_na_conta():
    sig = mare.volatilidades(_fechamentos(), _confirmacao(-0.15))
    depois = sig[POS_T : POS_T + 10]
    assert None not in depois
    assert sig[POS_T] > sig[POS_T - 1]


def test_queda_confirmada_mantem_a_calma_da_calculadora():
    calc = mare._Calculadora(_cesta(-0.15), _ibov())
    assert calc.leitura(T, 1.0).componentes["calma"] is not None
    # E o σ10 de t usa a queda de 14%: maior que o do pregão anterior.
    assert calc.sigmas[POS_T] > calc.sigmas[POS_T - 1]


def test_queda_nao_confirmada_sai():
    sig = mare.volatilidades(_fechamentos(), _confirmacao(-0.01))
    assert sig[POS_T : POS_T + 10] == [None] * 10
    calc = mare._Calculadora(_cesta(-0.01), _ibov())
    assert calc.sigmas[POS_T : POS_T + 10] == [None] * 10


def test_sinal_contrario_sai():
    sig = mare.volatilidades(_fechamentos(), _confirmacao(+0.08))
    assert sig[POS_T : POS_T + 10] == [None] * 10
    calc = mare._Calculadora(_cesta(+0.08), _ibov())
    assert calc.sigmas[POS_T : POS_T + 10] == [None] * 10


def test_amostra_pequena_no_pregao_sai():
    # 25 ações válidas na janela, mas só 19 com o pregão t.
    calc = mare._Calculadora(_cesta(-0.15, sem_t=6), _ibov())
    assert calc.amostra_ok
    assert calc.sigmas[POS_T : POS_T + 10] == [None] * 10
    # Com 20 ações no pregão, a amostra basta.
    calc = mare._Calculadora(_cesta(-0.15, sem_t=5), _ibov())
    assert None not in calc.sigmas[POS_T : POS_T + 10]


def test_sem_confirmacao_igual_a_hoje():
    fechamentos = _fechamentos()
    assert mare.volatilidades(fechamentos) == _volatilidades_de_18_11(fechamentos)
    for fech in (
        [100.0 * (1.01 if i % 2 else 0.99) ** i for i in range(40)],
        [100.0] * 11 + [101.0, 103.0],
        [100.0 + i for i in range(30)] + [60.0] + [61.0] * 15,
    ):
        assert mare.volatilidades(fech) == _volatilidades_de_18_11(fech)


def test_retorno_abaixo_do_limiar_nao_muda():
    fech = _fechamentos()
    fech = fech[:POS_T] + [fech[POS_T - 1] * 0.92] + fech[POS_T + 1 :]
    assert mare.volatilidades(fech, _confirmacao(+0.20)) == mare.volatilidades(fech)


# --- Ondas -------------------------------------------------------------------


def test_ondas_volta_a_ter_calma():
    payload = mare_historico.calcular(_cesta(-0.15), _ibov(), DIAS[-1])
    assert payload is not None
    leituras = payload["leituras"][-21:]
    assert len(leituras) == 21
    ondas = mare.nivel(leituras, 21, 15)
    assert ondas is not None
    assert "calma" not in ondas["ausentes"]

    # Sem a confirmação da cesta, a Calma de Ondas some, como antes da spec.
    payload = mare_historico.calcular(_cesta(-0.01), _ibov(), DIAS[-1])
    assert payload is not None
    ondas = mare.nivel(payload["leituras"][-21:], 21, 15)
    assert ondas is not None
    assert "calma" in ondas["ausentes"]


# --- método do card ----------------------------------------------------------


def test_metodo_do_card_cita_a_regra():
    from app.main import app as aplicacao

    html = TestClient(aplicacao).get("/mare").text
    assert (
        "Um dia de mais de 12% só fica de fora se as ações da cesta não "
        "acompanharam o movimento (erro provável da fonte)."
    ) in html
