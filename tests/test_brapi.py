import os
from unittest import mock
import pytest
import respx

from app.collectors import brapi


def test_brapi_cotacao_sucesso():
    with mock.patch.dict(os.environ, {"BRAPI_TOKEN": "test_token"}):
        with respx.mock:
            respx.get("https://brapi.dev/api/quote/PETR4?range=1y").respond(
                status_code=200,
                json={"results": [{"symbol": "PETR4", "regularMarketPrice": 40.0}]},
            )
            result = brapi.cotacao("PETR4", range="1y")
            assert result is not None
            assert result["symbol"] == "PETR4"
            assert result["regularMarketPrice"] == 40.0


def test_brapi_invalid_ticker():
    with pytest.raises(ValueError):
        brapi.cotacao("PETR4,VALE3")
    with pytest.raises(ValueError):
        brapi.cotacao("PETR4%2CVALE3")


def test_brapi_cotacoes_sucesso():
    with mock.patch.dict(os.environ, {"BRAPI_TOKEN": "test_token"}):
        with respx.mock:
            respx.get("https://brapi.dev/api/quote/PETR4").respond(
                status_code=200,
                json={"results": [{"symbol": "PETR4", "regularMarketPrice": 40.0}]},
            )
            respx.get("https://brapi.dev/api/quote/VALE3").respond(
                status_code=200,
                json={"results": [{"symbol": "VALE3", "regularMarketPrice": 60.0}]},
            )
            results = brapi.cotacoes(["PETR4", "VALE3"])
            assert len(results) == 2
            assert results["PETR4"]["regularMarketPrice"] == 40.0
            assert results["VALE3"]["regularMarketPrice"] == 60.0


def test_brapi_403_disjuntor():
    brapi._disjuntor_ate = None
    with mock.patch.dict(os.environ, {"BRAPI_TOKEN": "test_token"}):
        with respx.mock:
            respx.get("https://brapi.dev/api/quote/PETR4").respond(status_code=403)
            assert brapi.cotacao("PETR4") is None
            assert brapi._disjuntor_ate is not None
            result = brapi.cotacao("PETR4")
            assert result is None
    brapi._disjuntor_ate = None


def test_brapi_429_disjuntor_diario():
    brapi._disjuntor_ate = None
    with mock.patch.dict(os.environ, {"BRAPI_TOKEN": "test_token"}):
        with respx.mock:
            respx.get("https://brapi.dev/api/quote/PETR4").respond(
                status_code=429, text="too many requests"
            )
            assert brapi.cotacao("PETR4") is None
            assert brapi._disjuntor_ate is not None
            assert not brapi._esgotado_mensal
            result = brapi.cotacao("PETR4")
            assert result is None
    brapi._disjuntor_ate = None


def test_brapi_429_disjuntor_mensal():
    brapi._disjuntor_ate = None
    brapi._esgotado_mensal = False
    with mock.patch.dict(os.environ, {"BRAPI_TOKEN": "test_token"}):
        with respx.mock:
            respx.get("https://brapi.dev/api/quote/PETR4").respond(
                status_code=429, text="monthly quota exceeded"
            )
            assert brapi.cotacao("PETR4") is None
            assert brapi._disjuntor_ate is not None
            assert brapi._esgotado_mensal
            result = brapi.cotacao("PETR4")
            assert result is None
    brapi._disjuntor_ate = None
    brapi._esgotado_mensal = False
