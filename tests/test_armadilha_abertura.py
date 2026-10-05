import json
from unittest.mock import MagicMock
from app.collectors import armadilha_abertura


def test_fetch_yfinance(monkeypatch):
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "spark": {
            "result": [
                {
                    "symbol": "VALE3.SA",
                    "response": [
                        {
                            "indicators": {
                                "quote": [
                                    {
                                        "close": [100.0, 95.0],
                                        "open": [99.0, 102.0],
                                        "high": [100.5, 103.0],
                                    }
                                ]
                            }
                        }
                    ],
                }
            ]
        }
    }
    monkeypatch.setattr(
        "app.collectors.armadilha_abertura.fetch_with_retry",
        lambda *args, **kwargs: mock_response,
    )

    saved_data = []
    monkeypatch.setattr(
        "app.collectors.armadilha_abertura.save_armadilha_abertura_data",
        lambda d: saved_data.append(d),
    )

    ok = armadilha_abertura.collect_and_save()
    assert ok is True
    assert len(saved_data) == 1

    data = saved_data[0]
    assert data.fonte == "yfinance"
    alertas = json.loads(data.alertas_json)
    assert len(alertas) == 1
    assert alertas[0]["ticker"] == "VALE3"
