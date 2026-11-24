"""Aceite da spec 194: os pesos do Ibovespa saem de uma tabela só."""

from __future__ import annotations

import inspect
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pytest
import respx
from fastapi.testclient import TestClient

from app.collectors import anomalia_peso, concentracao, fator_peso_pesado
from app.collectors.pesos_ibovespa import PESOS_IBOVESPA, pesos
from app.database import (
    IbovespaData,
    get_latest_anomalia_peso_data,
    save_ibovespa_data,
)
from devagent.aceite import exigir_spec_done

SPARK = re.compile(r"https://query[12]\.finance\.yahoo\.com/v8/finance/spark.*")


def test_aceite_194_spec_done():
    exigir_spec_done("194")


def test_tabela_unica_e_funcao_pesos():
    assert PESOS_IBOVESPA == {
        "VALE3": 12.0,
        "PETR4": 8.0,
        "ITUB4": 7.0,
        "PETR3": 4.0,
        "BBDC4": 4.0,
        "B3SA3": 3.0,
        "WEGE3": 3.0,
        "ABEV3": 3.0,
        "BBDC3": 3.0,
        "BBAS3": 3.0,
    }
    assert list(PESOS_IBOVESPA) == list(concentracao.TICKERS_PESOS)
    assert pesos(("ITUB4",)) == {"ITUB4": 7.0}
    assert list(pesos(("PETR4", "VALE3"))) == ["PETR4", "VALE3"]
    with pytest.raises(KeyError):
        pesos(("XPTO3",))


def test_anomalia_de_peso_usa_o_peso_da_tabela(setup_db, monkeypatch):
    save_ibovespa_data(
        IbovespaData(
            timestamp=datetime.now(timezone.utc),
            current_price=130000.0,
            previous_close=129000.0,
            history_json="[]",
            fonte="mock",
        )
    )

    class Resposta:
        def json(self):
            return {
                "spark": {
                    "result": [
                        {
                            "symbol": "ITUB4.SA",
                            "response": [
                                {
                                    "meta": {
                                        "chartPreviousClose": 35.00,
                                        "regularMarketPrice": 35.70,
                                    }
                                }
                            ],
                        }
                    ]
                }
            }

    monkeypatch.setattr(
        "app.collectors.anomalia_peso.fetch_with_retry", lambda *a, **k: Resposta()
    )
    assert anomalia_peso.collect_and_save() is True
    dados = get_latest_anomalia_peso_data()
    assert dados is not None
    alertas = json.loads(dados.alertas_json)
    assert len(alertas) == 1
    assert alertas[0]["ticker"] == "ITUB4"
    assert alertas[0]["impacto"] == pytest.approx(180.6, abs=1e-6)


def _serie(simbolo: str, prev: float, atual: float) -> dict:
    return {
        "symbol": simbolo,
        "response": [{"indicators": {"quote": [{"close": [prev, atual]}]}}],
    }


def test_concentracao_usa_o_peso_da_tabela():
    resposta = {
        "spark": {
            "result": [
                _serie("ITUB4.SA", 35.00, 35.70),
                _serie("^BVSP", 129000.0, 130000.0),
            ]
        }
    }
    with respx.mock:
        respx.get(SPARK).respond(json=resposta)
        dados = concentracao.fetch_yfinance()
    assert dados is not None
    linhas = json.loads(dados.top3_json)
    itub = next(linha for linha in linhas if linha["ticker"] == "ITUB4")
    assert itub["pontos"] == pytest.approx(180.6, abs=1e-6)
    assert itub["peso"] == pytest.approx(0.07)


def test_mesmo_peso_nas_tres_constantes():
    fontes = [
        {t: p * 100 for t, p in concentracao.TICKERS_PESOS.items()},
        {t.removesuffix(".SA"): p for t, p in fator_peso_pesado.TICKERS_PESO.items()},
        dict(anomalia_peso.PESOS),
    ]
    for tabela in fontes:
        for ticker, peso in tabela.items():
            assert peso == pytest.approx(PESOS_IBOVESPA[ticker])


def test_coletores_sem_literal_de_peso():
    literal = re.compile(r'"[A-Z]{4}\d{1,2}(\.SA)?"\s*:\s*\d')
    for modulo in (concentracao, fator_peso_pesado, anomalia_peso):
        assert not literal.search(inspect.getsource(modulo)), modulo.__name__


def test_texto_do_fator_peso_pesado_sai_da_tabela():
    from app.main import app

    pagina = TestClient(app).get("/").text
    assert (
        "Pesos aproximados, somando 34%: VALE3 12, PETR4 8, ITUB4 7, PETR3 4, BBAS3 3"
        in pagina
    )
    assert "VALE3 12" not in Path("app/templates/index.html").read_text(
        encoding="utf-8"
    )
