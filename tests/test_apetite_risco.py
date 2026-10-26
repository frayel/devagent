import respx
import httpx
from app.collectors.apetite_risco import fetch_yfinance


@respx.mock
def test_fetch_yfinance_tomando_risco():
    mock_response = {
        "spark": {
            "result": [
                {
                    "symbol": "SMAL11.SA",
                    "response": [
                        {
                            "meta": {"chartPreviousClose": 100.0},
                            "indicators": {"quote": [{"close": [105.0]}]},
                        }
                    ],
                },
                {
                    "symbol": "^BVSP",
                    "response": [
                        {
                            "meta": {"chartPreviousClose": 100.0},
                            "indicators": {"quote": [{"close": [102.0]}]},
                        }
                    ],
                },
            ]
        }
    }
    respx.get(
        url__regex=r"https://query[12]\.finance\.yahoo\.com/v8/finance/spark.*"
    ).mock(return_value=httpx.Response(200, json=mock_response))
    data = fetch_yfinance()
    assert data is not None
    assert data.estado == "Tomando risco"
    assert data.diferenca == 3.0


@respx.mock
def test_fetch_yfinance_defensivo():
    mock_response = {
        "spark": {
            "result": [
                {
                    "symbol": "SMAL11.SA",
                    "response": [
                        {
                            "meta": {"chartPreviousClose": 100.0},
                            "indicators": {"quote": [{"close": [95.0]}]},
                        }
                    ],
                },
                {
                    "symbol": "^BVSP",
                    "response": [
                        {
                            "meta": {"chartPreviousClose": 100.0},
                            "indicators": {"quote": [{"close": [98.0]}]},
                        }
                    ],
                },
            ]
        }
    }
    respx.get(
        url__regex=r"https://query[12]\.finance\.yahoo\.com/v8/finance/spark.*"
    ).mock(return_value=httpx.Response(200, json=mock_response))
    data = fetch_yfinance()
    assert data is not None
    assert data.estado == "Defensivo"
    assert data.diferenca == -3.0


@respx.mock
def test_fetch_yfinance_neutro():
    mock_response = {
        "spark": {
            "result": [
                {
                    "symbol": "SMAL11.SA",
                    "response": [
                        {
                            "meta": {"chartPreviousClose": 100.0},
                            "indicators": {"quote": [{"close": [101.05]}]},
                        }
                    ],
                },
                {
                    "symbol": "^BVSP",
                    "response": [
                        {
                            "meta": {"chartPreviousClose": 100.0},
                            "indicators": {"quote": [{"close": [101.0]}]},
                        }
                    ],
                },
            ]
        }
    }
    respx.get(
        url__regex=r"https://query[12]\.finance\.yahoo\.com/v8/finance/spark.*"
    ).mock(return_value=httpx.Response(200, json=mock_response))
    data = fetch_yfinance()
    assert data is not None
    assert data.estado == "Neutro"
    assert round(data.diferenca, 2) == 0.05
