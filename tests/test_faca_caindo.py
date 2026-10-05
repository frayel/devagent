import json
from app.collectors import faca_caindo


def test_fetch_yfinance_success(monkeypatch):
    class MockResponse:
        def __init__(self, json_data):
            self.json_data = json_data
            self.status_code = 200

        def json(self):
            return self.json_data

        def raise_for_status(self):
            pass

    def mock_fetch(*args, **kwargs):
        url = args[0] if args else kwargs.get("url")
        if "PETR4" not in url:
            return MockResponse({"spark": {"result": []}})

        # Return 1 ticker with 3 drops, 1 with 2 drops, and rest 0

        return MockResponse(
            {
                "spark": {
                    "result": [
                        {
                            "symbol": "PETR4.SA",
                            "response": [
                                {
                                    "indicators": {
                                        "quote": [{"close": [10.0, 9.0, 8.0, 7.0]}]
                                    }
                                }
                            ],
                        },
                        {
                            "symbol": "VALE3.SA",
                            "response": [
                                {
                                    "indicators": {
                                        "quote": [{"close": [10.0, 10.0, 9.0, 8.0]}]
                                    }
                                }
                            ],
                        },
                    ]
                }
            }
        )

    monkeypatch.setattr(faca_caindo, "fetch_with_retry", mock_fetch)

    data = faca_caindo.fetch_yfinance()
    assert data is not None
    assert data.fonte == "yfinance"
    alertas = json.loads(data.alertas_json)
    assert len(alertas) == 1
    assert alertas[0]["ticker"] == "PETR4"
    assert alertas[0]["dias"] == 3


def test_fetch_yfinance_empty(monkeypatch):
    class MockResponse:
        def __init__(self, json_data):
            self.json_data = json_data
            self.status_code = 200

        def json(self):
            return self.json_data

        def raise_for_status(self):
            pass

    def mock_fetch(*args, **kwargs):
        return MockResponse({"spark": {"result": []}})

    monkeypatch.setattr(faca_caindo, "fetch_with_retry", mock_fetch)

    data = faca_caindo.fetch_yfinance()
    assert data is not None
    alertas = json.loads(data.alertas_json)
    assert len(alertas) == 0
