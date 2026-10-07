from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_api_snapshot_radar_volume():
    response = client.get("/api/snapshot")
    assert response.status_code == 200
    data = response.json()
    assert "radar_volume" in data["paineis"]


def test_api_snapshot_apetite_risco():
    response = client.get("/api/snapshot")
    assert response.status_code == 200
    data = response.json()
    assert "apetite_risco" in data["paineis"]


def test_api_snapshot_compradores_fundo():
    response = client.get("/api/snapshot")
    assert response.status_code == 200
    data = response.json()
    assert "compradores_fundo" in data["paineis"]


def test_api_snapshot_volatilidade_silenciosa():
    response = client.get("/api/snapshot")
    assert response.status_code == 200
    data = response.json()
    assert "volatilidade_silenciosa" in data["paineis"]
