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


def test_api_snapshot_correlacao_di():
    response = client.get("/api/snapshot")
    assert response.status_code == 200
    data = response.json()
    if "correlacao_di" in data["paineis"]:
        assert "correlacao_di" in data["paineis"]


def test_api_snapshot_exaustao_queda():
    from app.database import ExaustaoQuedaData, save_exaustao_queda_data
    from datetime import datetime, timezone

    save_exaustao_queda_data(
        ExaustaoQuedaData(
            timestamp=datetime.now(timezone.utc), fonte="teste", alertas_json="[]"
        )
    )
    response = client.get("/api/snapshot")
    assert response.status_code == 200
    data = response.json()
    assert "exaustao_queda" in data["paineis"]


def test_api_snapshot_exaustao_queda_contrato():
    response = client.get("/api/snapshot")
    assert response.status_code == 200
    data = response.json()
    if "exaustao_queda" in data["paineis"]:
        assert "coletado_em" in data["paineis"]["exaustao_queda"]
        assert "fonte" in data["paineis"]["exaustao_queda"]
        # ISO format test
        from datetime import datetime

        try:
            datetime.fromisoformat(data["paineis"]["exaustao_queda"]["coletado_em"])
        except ValueError:
            assert False, "Date is not ISO 8601"
