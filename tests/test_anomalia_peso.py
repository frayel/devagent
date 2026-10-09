import json
from datetime import datetime, timezone


def test_anomalia_peso_collector(setup_db, monkeypatch):
    import app.collectors.anomalia_peso as anomalia_peso
    from app.database import get_latest_anomalia_peso_data, get_connection, init_db

    init_db()
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO ibovespa_cache (timestamp, current_price, previous_close, history_json, fonte)
        VALUES (?, ?, ?, ?, ?)
        """,
        (datetime.now(timezone.utc).isoformat(), 100000, 100000, "[]", "test"),
    )
    conn.commit()

    mock_response = {
        "spark": {
            "result": [
                {
                    "symbol": "VALE3.SA",
                    "response": [
                        {
                            "meta": {
                                "chartPreviousClose": 100.0,
                                "regularMarketPrice": 110.0,
                            }
                        }
                    ],
                },
                {
                    "symbol": "PETR4.SA",
                    "response": [
                        {
                            "meta": {
                                "chartPreviousClose": 50.0,
                                "regularMarketPrice": 45.0,
                            }
                        }
                    ],
                },
            ]
        }
    }

    def mock_fetch(*args, **kwargs):
        class MockResp:
            def json(self):
                return mock_response

            def raise_for_status(self):
                pass

        return MockResp()

    monkeypatch.setattr("app.collectors.anomalia_peso.fetch_with_retry", mock_fetch)

    ok = anomalia_peso.collect_and_save()
    assert ok is True

    data = get_latest_anomalia_peso_data()
    assert data is not None
    assert data.fonte == "yfinance"

    alertas = json.loads(data.alertas_json)
    assert len(alertas) == 2

    assert alertas[0]["ticker"] == "VALE3"
    assert alertas[0]["impacto"] == 1200.0
    assert alertas[1]["ticker"] == "PETR4"
    assert alertas[1]["impacto"] == -800.0
