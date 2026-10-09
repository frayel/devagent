import json
from datetime import datetime, timezone

from app.collectors import radar_inflexao


def test_radar_inflexao_collector(setup_db, monkeypatch):
    from app.database import get_latest_radar_inflexao_data

    monkeypatch.setattr("app.collectors.radar_inflexao.TICKERS", ["PETR4", "VALE3"])

    mock_response = {
        "spark": {
            "result": [
                {
                    "symbol": "PETR4.SA",
                    "response": [
                        {
                            "indicators": {
                                "quote": [
                                    {
                                        "close": [
                                            10.0,
                                            9.0,
                                            8.0,
                                            7.0,
                                            6.0,
                                            5.0,
                                            4.0,
                                            3.0,
                                            2.0,
                                            1.0,
                                            0.5,
                                            0.4,
                                            0.3,
                                            0.2,
                                            0.1,
                                            0.5,
                                        ]
                                    }
                                ]
                            }
                        }
                    ],
                },
                {
                    "symbol": "VALE3.SA",
                    "response": [{"indicators": {"quote": [{"close": [100.0] * 16}]}}],
                },
            ]
        }
    }

    class MockResponse:
        def json(self):
            return mock_response

    def mock_fetch(*args, **kwargs):
        return MockResponse()

    monkeypatch.setattr("app.collectors.radar_inflexao.fetch_with_retry", mock_fetch)

    radar_inflexao.collect_and_save()

    data = get_latest_radar_inflexao_data()
    assert data is not None
    assert data.fonte == "yfinance"

    alertas = json.loads(data.alertas_json)
    assert len(alertas) == 1
    assert alertas[0]["ticker"] == "PETR4"
    assert alertas[0]["variacao_hoje"] > 2
    assert alertas[0]["retorno_acumulado"] < -5


def test_radar_inflexao_view_snapshot(setup_db):
    from app.database import RadarInflexaoData, save_radar_inflexao_data
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)

    alertas = [{"ticker": "WEGE3", "variacao_hoje": 5.2, "retorno_acumulado": -15.5}]

    save_radar_inflexao_data(
        RadarInflexaoData(
            timestamp=datetime.now(timezone.utc),
            alertas_json=json.dumps(alertas),
            fonte="yfinance",
        )
    )

    response = client.get("/api/snapshot")
    assert response.status_code == 200

    data = response.json()
    assert "radar_inflexao" in data["paineis"]
    assert len(data["paineis"]["radar_inflexao"]["alertas"]) == 1
    assert data["paineis"]["radar_inflexao"]["alertas"][0]["ticker"] == "WEGE3"
