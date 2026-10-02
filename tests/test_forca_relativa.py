import json
from app.collectors import forca_relativa
from app.database import ForcaRelativaData


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
        if "^BVSP" in url:
            return MockResponse(
                {
                    "chart": {
                        "result": [
                            {
                                "indicators": {
                                    "quote": [
                                        {
                                            "close": [100000.0] * 29
                                            + [110000.0]  # 30 valid days, return = 10%
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                }
            )
        elif "spark" in url:
            # We just return data for PETR4 and VALE3
            return MockResponse(
                {
                    "spark": {
                        "result": [
                            {
                                "symbol": "PETR4.SA",
                                "response": [
                                    {
                                        "indicators": {
                                            "quote": [
                                                {
                                                    "close": [20.0] * 29
                                                    + [25.0]  # Return = 25%
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
                                                    "close": [50.0] * 29
                                                    + [47.5]  # Return = -5%
                                                }
                                            ]
                                        }
                                    }
                                ],
                            },
                        ]
                    }
                }
            )

    monkeypatch.setattr("app.collectors.forca_relativa.fetch_with_retry", mock_fetch)
    monkeypatch.setattr("app.collectors.forca_relativa.TICKERS", ["PETR4", "VALE3"])

    data = forca_relativa.fetch_yfinance()

    assert data is not None
    assert isinstance(data, ForcaRelativaData)

    maior = json.loads(data.maior_json)
    assert maior["ticker"] == "PETR4"
    # return PETR4 (0.25) - IBOV (0.1) = 0.15
    assert abs(maior["forca_relativa"] - 0.15) < 0.001

    menor = json.loads(data.menor_json)
    assert menor["ticker"] == "VALE3"
    # return VALE3 (-0.05) - IBOV (0.1) = -0.15
    assert abs(menor["forca_relativa"] - (-0.15)) < 0.001


def test_fetch_yfinance_no_ibov_data(monkeypatch):
    class MockResponse:
        def __init__(self):
            self.status_code = 200

        def json(self):
            return {
                "chart": {
                    "result": [{"indicators": {"quote": [{"close": [100000.0] * 10}]}}]
                }
            }  # Only 10 days

        def raise_for_status(self):
            pass

    monkeypatch.setattr(
        "app.collectors.forca_relativa.fetch_with_retry",
        lambda *args, **kwargs: MockResponse(),
    )

    data = forca_relativa.fetch_yfinance()
    assert data is None
