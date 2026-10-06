import pytest
import respx
import httpx

from app.collectors import concentracao_setorial
from app.database import get_latest_concentracao_setorial_data


@pytest.fixture
def mock_brapi_response():
    return {
        "results": [
            {
                "symbol": "PETR4",
                "regularMarketPrice": 30.5,
                "regularMarketPreviousClose": 30.0,
            },
            {
                "symbol": "VALE3",
                "regularMarketPrice": 61.2,
                "regularMarketPreviousClose": 60.0,
            },
            {
                "symbol": "ITUB4",
                "regularMarketPrice": 25.0,
                "regularMarketPreviousClose": 24.5,
            },
        ]
    }


@pytest.fixture
def mock_yfinance_response():
    return {
        "spark": {
            "result": [
                {
                    "symbol": "PETR4.SA",
                    "response": [
                        {
                            "meta": {
                                "regularMarketPrice": 30.5,
                                "chartPreviousClose": 30.0,
                            }
                        }
                    ],
                },
                {
                    "symbol": "VALE3.SA",
                    "response": [
                        {
                            "meta": {
                                "regularMarketPrice": 61.2,
                                "chartPreviousClose": 60.0,
                            }
                        }
                    ],
                },
            ]
        }
    }


def test_coleta_concentracao_setorial_com_brapi(
    mock_brapi_response, monkeypatch, setup_db
):
    monkeypatch.setenv("BRAPI_TOKEN", "fake_token")

    with respx.mock:
        respx.get(url__startswith="https://brapi.dev").mock(
            return_value=httpx.Response(200, json=mock_brapi_response)
        )

        sucesso = concentracao_setorial.collect_and_save()
        assert sucesso is True

        data = get_latest_concentracao_setorial_data()
        assert data is not None
        assert data.fonte == "brapi"
        assert data.setor_destaque in [
            "Finance",
            "Energy Minerals",
            "Non-Energy Minerals",
        ]


def test_coleta_concentracao_setorial_com_yfinance_fallback(
    mock_yfinance_response, monkeypatch, setup_db
):
    monkeypatch.delenv("BRAPI_TOKEN", raising=False)

    with respx.mock:
        respx.get(url__startswith="https://brapi.dev").mock(
            return_value=httpx.Response(500)
        )
        respx.get(url__startswith="https://query1.finance.yahoo.com").mock(
            return_value=httpx.Response(200, json=mock_yfinance_response)
        )

        sucesso = concentracao_setorial.collect_and_save()
        assert sucesso is True

        data = get_latest_concentracao_setorial_data()
        assert data is not None
        assert data.fonte == "yfinance"


def test_coleta_concentracao_setorial_falha_total(monkeypatch, setup_db):
    monkeypatch.delenv("BRAPI_TOKEN", raising=False)

    with respx.mock:
        respx.get(url__startswith="https://brapi.dev").mock(
            return_value=httpx.Response(500)
        )
        respx.get(url__startswith="https://query1.finance.yahoo.com").mock(
            return_value=httpx.Response(500)
        )

        sucesso = concentracao_setorial.collect_and_save()
        assert sucesso is False

        data = get_latest_concentracao_setorial_data()
        assert data is None
