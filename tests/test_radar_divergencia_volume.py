import json
from unittest.mock import patch, MagicMock
from app.collectors.radar_divergencia_volume import collect_and_save
from app.database import get_latest_radar_divergencia_volume_data


def test_radar_divergencia_volume_collector():
    with patch(
        "app.collectors.radar_divergencia_volume.fetch_with_retry"
    ) as mock_fetch:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "chart": {
                "result": [
                    {
                        "indicators": {
                            "quote": [
                                {
                                    "open": [10.0] * 5,
                                    "close": [10.0, 10.1, 10.2, 10.3, 10.5],
                                    "volume": [5000, 5000, 5000, 1000, 1000],
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

        data = get_latest_radar_divergencia_volume_data()
        assert data is not None

        alertas = json.loads(data.alertas_json)
        assert len(alertas) > 0
        assert "ticker" in alertas[0]
        assert alertas[0]["var_volume"] < 0
        assert alertas[0]["alta_acumulada"] > 0

        # Test main snapshot
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        response = client.get("/api/snapshot")
        assert response.status_code == 200
        snap = response.json()
        assert "divergencia_volume" in snap["paineis"]
        assert len(snap["paineis"]["divergencia_volume"]["alertas"]) > 0
        assert "ticker" in snap["paineis"]["divergencia_volume"]["alertas"][0]
