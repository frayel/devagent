import json
from unittest.mock import MagicMock
from app.collectors import escudo_quedas


def test_fetch_yfinance(monkeypatch):
    mock_response_ibov = MagicMock()
    mock_response_ibov.raise_for_status = MagicMock()
    mock_response_ibov.json.return_value = {
        "chart": {
            "result": [
                {
                    "timestamp": list(range(1, 32)),
                    "indicators": {"quote": [{"close": [100.0] * 29 + [90.0, 85.0]}]},
                }
            ]
        }
    }

    mock_response_stocks = MagicMock()
    mock_response_stocks.raise_for_status = MagicMock()
    mock_response_stocks.json.return_value = {
        "spark": {
            "result": [
                {
                    "symbol": "PETR4.SA",
                    "response": [
                        {
                            "timestamp": list(range(1, 32)),
                            "indicators": {
                                "quote": [{"close": [20.0] * 29 + [21.0, 22.0]}]
                            },
                        }
                    ],
                }
            ]
        }
    }

    def mock_fetch(*args, **kwargs):
        url = args[0]
        if "^BVSP" in url:
            return mock_response_ibov
        return mock_response_stocks

    monkeypatch.setattr("app.collectors.escudo_quedas.fetch_with_retry", mock_fetch)
    monkeypatch.setattr("app.collectors.escudo_quedas.TICKERS", ["PETR4"])

    data = escudo_quedas.fetch_yfinance()
    assert data is not None
    assert data.fonte == "yfinance"

    parsed = json.loads(data.top3_json)
    assert parsed["qtd_quedas_ibov"] == 2
    assert len(parsed["top3"]) == 1
    assert parsed["top3"][0]["ticker"] == "PETR4"
    assert parsed["top3"][0]["dias_positivos"] == 2
