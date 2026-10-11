import json
from unittest.mock import patch, MagicMock
from app.collectors.falso_rompimento import collect_and_save
from app.database import get_latest_falso_rompimento_data


def test_falso_rompimento_collector():
    with patch("app.collectors.falso_rompimento.fetch_with_retry") as mock_fetch:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "chart": {
                "result": [
                    {
                        "indicators": {
                            "quote": [
                                {
                                    "high": [
                                        10.5,
                                        11.0,
                                    ],  # D-0 has higher high (11.0 > 10.5)
                                    "close": [
                                        10.2,
                                        10.0,
                                    ],  # D-0 close is below D-1 close (10.0 < 10.2)
                                    "volume": [
                                        1000,
                                        2000,
                                    ],  # D-0 volume is higher (2000 > 1000)
                                }
                            ]
                        }
                    }
                ]
            }
        }
        mock_fetch.return_value = mock_resp

        res = collect_and_save()
        assert res is True

        data = get_latest_falso_rompimento_data()
        assert data is not None

        alertas = json.loads(data.alertas_json)
        assert len(alertas) > 0
        assert "ticker" in alertas[0]
        assert alertas[0]["var_volume"] > 0
        assert alertas[0]["variacao"] < 0

        # Test main snapshot
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        response = client.get("/api/snapshot")
        assert response.status_code == 200
        snap = response.json()
        assert "falso_rompimento" in snap["paineis"]
        assert len(snap["paineis"]["falso_rompimento"]) > 0
        assert "ticker" in snap["paineis"]["falso_rompimento"][0]
