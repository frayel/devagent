import json
from unittest.mock import patch, MagicMock
from app.collectors.esforco_resultado import collect_and_save
from app.database import get_latest_esforco_resultado_data


def test_esforco_resultado_collector():
    with patch("app.collectors.esforco_resultado.fetch_with_retry") as mock_fetch:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "chart": {
                "result": [
                    {
                        "indicators": {
                            "quote": [
                                {
                                    "open": [10.0] * 20 + [10.0],
                                    "close": [10.0] * 20 + [10.02],
                                    "volume": [1000] * 20 + [5000],
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

        data = get_latest_esforco_resultado_data()
        assert data is not None

        alertas = json.loads(data.alertas_json)
        assert len(alertas) > 0
        assert alertas[0]["ticker"] == "PETR4"
        assert alertas[0]["vol_ratio"] == 5.0
        assert alertas[0]["price_var"] == 0.2

        # Test main snapshot
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        response = client.get("/api/snapshot")
        assert response.status_code == 200
        snap = response.json()
        assert "esforco_resultado" in snap["paineis"]
        assert len(snap["paineis"]["esforco_resultado"]) > 0
        assert snap["paineis"]["esforco_resultado"][0]["ticker"] == "PETR4"
