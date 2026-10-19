from fastapi.testclient import TestClient
from app.main import app as fastapi_app
import app.main

client = TestClient(fastapi_app)


def test_pagina_consultor_sem_senha(monkeypatch):
    monkeypatch.delenv("CONSULTOR_SENHA", raising=False)

    response = client.get("/consultor")
    assert response.status_code == 200
    assert "Consultor de Investimentos" in response.text


def test_api_consultor_sem_senha(monkeypatch):
    monkeypatch.delenv("CONSULTOR_SENHA", raising=False)

    response = client.get("/api/consultor")
    assert response.status_code == 200
    assert "ativos_avaliados" in response.json()


def test_snapshot_consultor_metadados():
    response = client.get("/api/snapshot")
    assert response.status_code == 200
    data = response.json()
    assert "consultor" in data
    assert "ativos_avaliados" in data["consultor"]
    assert "composicao_vigente_ate" in data["consultor"]


def test_consultor_com_senha_sem_auth(monkeypatch):
    monkeypatch.setenv("CONSULTOR_SENHA", "senha_secreta")

    response = client.get("/consultor")
    assert response.status_code == 401

    response = client.get("/api/consultor")
    assert response.status_code == 401


def test_consultor_com_senha_auth_valida(monkeypatch):
    monkeypatch.setenv("CONSULTOR_SENHA", "senha_secreta")

    response = client.get("/consultor", auth=("consultor", "senha_secreta"))
    assert response.status_code == 200

    response = client.get("/api/consultor", auth=("consultor", "senha_secreta"))
    assert response.status_code == 200


def test_pagina_consultor_desatualizada(monkeypatch):
    monkeypatch.delenv("CONSULTOR_SENHA", raising=False)

    def mock_hoje():
        return True

    monkeypatch.setattr(app.main, "composicao_esta_desatualizada", mock_hoje)

    response = client.get("/consultor")
    assert response.status_code == 200
    assert "Composição do Ibovespa possivelmente desatualizada" in response.text
