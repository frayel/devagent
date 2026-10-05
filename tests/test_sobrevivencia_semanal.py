import json

import pytest
import respx
import httpx

from app.collectors.sobrevivencia_semanal import coletar


@pytest.fixture
def mock_yfinance_success():
    with respx.mock(assert_all_called=False) as respx_mock:
        # Mock para a primeira requisição (PETR4, etc)
        respx_mock.get(
            url__startswith="https://query1.finance.yahoo.com/v7/finance/spark"
        ).mock(
            return_value=httpx.Response(
                200,
                json={
                    "spark": {
                        "result": [
                            {
                                "symbol": "WEGE3.SA",
                                "response": [
                                    {
                                        "indicators": {
                                            "quote": [
                                                {
                                                    "close": [
                                                        10.0,
                                                        11.0,
                                                        12.0,
                                                        13.0,
                                                        14.0,
                                                        15.0,
                                                    ]
                                                }
                                            ]
                                        }
                                    }
                                ],
                            },
                            {
                                "symbol": "VALE3.SA",
                                "response": [
                                    {
                                        "indicators": {
                                            "quote": [
                                                {
                                                    "close": [
                                                        10.0,
                                                        9.0,
                                                        8.0,
                                                        7.0,
                                                        6.0,
                                                        5.0,
                                                    ]
                                                }
                                            ]
                                        }
                                    }
                                ],
                            },
                        ]
                    }
                },
            )
        )
        yield respx_mock


def test_sobrevivencia_semanal_success(mock_yfinance_success):
    data = coletar()
    assert data is not None
    assert data.fonte == "yfinance"
    alertas = json.loads(data.alertas_json)
    # WEGE3 teve altas seguidas, VALE3 não
    assert len(alertas) > 0
    assert alertas[0]["ticker"] == "WEGE3"
    assert alertas[0]["dias_consecutivos"] == 5


@pytest.fixture
def mock_yfinance_failure():
    with respx.mock(assert_all_called=False) as respx_mock:
        respx_mock.get(
            url__startswith="https://query1.finance.yahoo.com/v7/finance/spark"
        ).mock(return_value=httpx.Response(500))
        yield respx_mock


def test_sobrevivencia_semanal_failure(mock_yfinance_failure):
    data = coletar()
    assert data is None


@pytest.fixture
def mock_yfinance_empty():
    with respx.mock(assert_all_called=False) as respx_mock:
        respx_mock.get(
            url__startswith="https://query1.finance.yahoo.com/v7/finance/spark"
        ).mock(
            return_value=httpx.Response(
                200,
                json={
                    "spark": {
                        "result": [
                            {
                                "symbol": "VALE3.SA",
                                "response": [
                                    {
                                        "indicators": {
                                            "quote": [
                                                {
                                                    "close": [
                                                        10.0,
                                                        9.0,
                                                        8.0,
                                                        7.0,
                                                        6.0,
                                                        5.0,
                                                    ]
                                                }
                                            ]
                                        }
                                    }
                                ],
                            }
                        ]
                    }
                },
            )
        )
        yield respx_mock


def test_sobrevivencia_semanal_empty(mock_yfinance_empty):
    data = coletar()
    assert data is not None
    alertas = json.loads(data.alertas_json)
    assert len(alertas) == 0
