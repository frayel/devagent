import pytest
import json
from unittest.mock import MagicMock
from app.collectors import fator_mola
from app.database import FatorMolaData

def test_fetch_yfinance(monkeypatch):
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "spark": {
            "result": [
                {
                    "symbol": "PETR4.SA",
                    "response": [
                        {
                            "meta": {
                                "regularMarketPrice": 40.00,
                                "regularMarketDayLow": 35.00
                            }
                        }
                    ]
                },
                {
                    "symbol": "VALE3.SA",
                    "response": [
                        {
                            "meta": {
                                "regularMarketPrice": 60.00,
                                "regularMarketDayLow": 55.00
                            }
                        }
                    ]
                }
            ]
        }
    }
    monkeypatch.setattr('app.collectors.fator_mola.fetch_with_retry', lambda *args, **kwargs: mock_response)
    monkeypatch.setattr('app.collectors.fator_mola.TICKERS', ['PETR4', 'VALE3'])

    data = fator_mola.fetch_yfinance()
    assert data is not None
    assert data.fonte == "yfinance"

    top3 = json.loads(data.top3_json)
    assert len(top3) == 2
    assert top3[0]["ticker"] == "PETR4"
    assert top3[0]["mola_percent"] > 14.0

def test_fetch_yfinance_no_data(monkeypatch):
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {}
    monkeypatch.setattr('app.collectors.fator_mola.fetch_with_retry', lambda *args, **kwargs: mock_response)

    data = fator_mola.fetch_yfinance()
    assert data is not None
    assert json.loads(data.top3_json) == []

def test_fetch_brapi(monkeypatch):
    monkeypatch.setenv("BRAPI_TOKEN", "fake_token")
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "results": [
            {
                "symbol": "ITUB4",
                "regularMarketPrice": 35.00,
                "regularMarketDayLow": 33.00
            }
        ]
    }
    monkeypatch.setattr('app.collectors.fator_mola.fetch_with_retry', lambda *args, **kwargs: mock_response)

    data = fator_mola.fetch_brapi()
    assert data is not None
    assert data.fonte == "brapi"

    top3 = json.loads(data.top3_json)
    assert len(top3) == 1
    assert top3[0]["ticker"] == "ITUB4"
