import json

import respx
import httpx

from app.database import VolatilidadeSilenciosaData
from app.collectors.volatilidade_silenciosa import fetch_yfinance


@respx.mock
def test_fetch_yfinance_success():
    yfinance_response = {
        "spark": {
            "result": [
                {
                    "symbol": "PETR4.SA",
                    "response": [
                        {
                            "indicators": {
                                "quote": [
                                    {
                                        "open": [10.0],
                                        "high": [11.0],
                                        "low": [9.0],
                                        "close": [10.02],
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
                                        "open": [10.0],
                                        "high": [12.0],
                                        "low": [8.0],
                                        "close": [10.01],
                                    }
                                ]
                            }
                        }
                    ],
                },
                {
                    "symbol": "ITUB4.SA",
                    "response": [
                        {
                            "indicators": {
                                "quote": [
                                    {
                                        "open": [10.0],
                                        "high": [10.5],
                                        "low": [9.5],
                                        "close": [10.6],
                                    }
                                ]
                            }
                        }
                    ],
                },
            ]
        }
    }

    respx.get(url__startswith="https://query1.finance.yahoo.com/v7/finance/spark").mock(
        return_value=httpx.Response(200, json=yfinance_response)
    )

    data = fetch_yfinance()
    assert isinstance(data, VolatilidadeSilenciosaData)
    assert data.fonte == "yfinance"

    alertas = json.loads(data.alertas_json)
    assert len(alertas) == 2

    # VALE3 should be first (high amplitude: (12-8)/8 = 50%)
    assert alertas[0]["ticker"] == "VALE3"
    assert alertas[0]["amplitude"] == 50.0
    assert abs(alertas[0]["variacao"]) <= 0.5

    # PETR4 should be second (high amplitude: (11-9)/9 = 22.2%)
    assert alertas[1]["ticker"] == "PETR4"
    assert round(alertas[1]["amplitude"], 1) == 22.2
    assert abs(alertas[1]["variacao"]) <= 0.5


@respx.mock
def test_fetch_yfinance_no_data():
    respx.get(url__startswith="https://query1.finance.yahoo.com/v7/finance/spark").mock(
        return_value=httpx.Response(200, json={"spark": {"result": []}})
    )

    data = fetch_yfinance()
    assert data.alertas_json == "[]"


@respx.mock
def test_fetch_yfinance_http_error():
    respx.get(url__startswith="https://query1.finance.yahoo.com/v7/finance/spark").mock(
        return_value=httpx.Response(500)
    )

    data = fetch_yfinance()
    assert data is None
