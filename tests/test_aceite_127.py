from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_api_coleta_tem_dados(monkeypatch):
    monkeypatch.delenv("SENHA", raising=False)
    monkeypatch.setenv("RENDER", "1")
    monkeypatch.delenv("DATABASE_URL", raising=False)

    response = client.get("/api/coleta")
    assert response.status_code == 200
    data = response.json()
    assert "ligada" in data
    assert "banco" in data
    assert "aviso" in data
    assert (
        data["aviso"]
        == "Banco persistente não configurado: dados se perdem ao reiniciar"
    )


def test_api_coleta_senha(monkeypatch):
    monkeypatch.setenv("CONSULTOR_SENHA", "minhasenha")
    monkeypatch.delenv("SENHA", raising=False)

    # Sem credencial
    response = client.get("/api/coleta")
    assert response.status_code == 401

    # Credencial errada
    response = client.get("/api/coleta", auth=("consultor", "errada"))
    assert response.status_code == 401

    # Credencial certa
    response = client.get("/api/coleta", auth=("consultor", "minhasenha"))
    assert response.status_code == 200


def test_consultor_cache_status(monkeypatch):
    monkeypatch.delenv("SENHA", raising=False)

    # Primeira chamada
    response1 = client.get("/api/consultor")
    assert response1.status_code == 200
    data1 = response1.json()
    assert data1["cache"] is False

    # Segunda chamada (deve usar cache)
    response2 = client.get("/api/consultor")
    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["cache"] is True
