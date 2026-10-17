import json
from unittest.mock import MagicMock
from app.collectors import fator_mola


def test_fetch_yfinance(monkeypatch):
    def mock_fetch(symbols, *args, **kwargs):
        res = []
        if "PETR4" in symbols:
            res.append(
                {
                    "symbol": "PETR4.SA",
                    "response": [
                        {
                            "meta": {
                                "regularMarketPrice": 40.00,
                                "regularMarketDayLow": 35.00,
                            }
                        }
                    ],
                }
            )
        if "VALE3" in symbols:
            res.append(
                {
                    "symbol": "VALE3.SA",
                    "response": [
                        {
                            "meta": {
                                "regularMarketPrice": 60.00,
                                "regularMarketDayLow": 50.00,
                            }
                        }
                    ],
                }
            )
        return res

    monkeypatch.setattr(
        "app.collectors.fator_mola.fetch_historico_diario_yfinance_spark",
        mock_fetch,
    )
    monkeypatch.setattr("app.collectors.fator_mola.TICKERS", ["PETR4", "VALE3"])

    data = fator_mola.fetch_yfinance()
    assert data is not None
    assert data.fonte == "yfinance"

    top3 = json.loads(data.top3_json)
    assert len(top3) == 2
    assert top3[0]["ticker"] == "VALE3"
    assert top3[0]["mola_percent"] == 20.0


def test_fetch_yfinance_no_data(monkeypatch):
    def mock_fetch(*args, **kwargs):
        return []

    monkeypatch.setattr(
        "app.collectors.fator_mola.fetch_historico_diario_yfinance_spark",
        mock_fetch,
    )

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
                "regularMarketDayLow": 33.00,
            }
        ]
    }
    monkeypatch.setattr(
        "app.collectors.fator_mola.fetch_with_retry",
        lambda *args, **kwargs: mock_response,
    )

    data = fator_mola.fetch_brapi()
    assert data is not None
    assert data.fonte == "brapi"

    top3 = json.loads(data.top3_json)
    assert len(top3) == 1
    assert top3[0]["ticker"] == "ITUB4"
