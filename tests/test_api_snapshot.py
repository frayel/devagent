from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_api_snapshot_radar_volume():
    response = client.get("/api/snapshot")
    assert response.status_code == 200
    data = response.json()
    assert "radar_volume" in data["paineis"]
