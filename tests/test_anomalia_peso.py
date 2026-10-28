from datetime import datetime, timezone
from app.database import IbovespaData, save_ibovespa_data, get_latest_anomalia_peso_data
from app.collectors.anomalia_peso import collect_and_save


def test_anomalia_peso_collector_new_format(setup_db, monkeypatch):
    save_ibovespa_data(
        IbovespaData(
            timestamp=datetime.now(timezone.utc),
            current_price=130000.0,
            previous_close=129000.0,
            history_json="[]",
            fonte="mock",
        )
    )

    class MockResponse:
        def json(self):
            return {
                "VALE3.SA": {
                    "symbol": "VALE3.SA",
                    "previousClose": 60.0,
                    "close": [63.0],
                }
            }

    monkeypatch.setattr(
        "app.collectors.anomalia_peso.fetch_with_retry",
        lambda *args, **kwargs: MockResponse(),
    )

    assert collect_and_save() is True
    data = get_latest_anomalia_peso_data()
    assert data is not None
    assert "VALE3" in data.alertas_json


def test_anomalia_peso_collector_old_format(setup_db, monkeypatch):
    save_ibovespa_data(
        IbovespaData(
            timestamp=datetime.now(timezone.utc),
            current_price=130000.0,
            previous_close=129000.0,
            history_json="[]",
            fonte="mock",
        )
    )

    class MockResponse:
        def json(self):
            return {
                "spark": {
                    "result": [
                        {
                            "symbol": "VALE3.SA",
                            "response": [
                                {
                                    "meta": {
                                        "previousClose": 60.0,
                                        "regularMarketPrice": 63.0,
                                    }
                                }
                            ],
                        }
                    ]
                }
            }

    monkeypatch.setattr(
        "app.collectors.anomalia_peso.fetch_with_retry",
        lambda *args, **kwargs: MockResponse(),
    )

    assert collect_and_save() is True
    data = get_latest_anomalia_peso_data()
    assert data is not None
    assert "VALE3" in data.alertas_json
