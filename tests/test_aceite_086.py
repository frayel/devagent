from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_aceite_086_api_traz_informacoes_de(monkeypatch):
    monkeypatch.delenv("CONSULTOR_SENHA", raising=False)
    resp = client.get("/api/consultor")
    assert resp.status_code == 200
    dados = resp.json()
    assert "informacoes_de" in dados


def test_aceite_086_html_traz_selos(monkeypatch):
    monkeypatch.delenv("CONSULTOR_SENHA", raising=False)
    resp = client.get("/consultor")
    assert resp.status_code == 200
    html = resp.text
    assert "Informações de" in html
