import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import get_connection, save_apetite_risco_data, ApetiteRiscoData
from app.banco import get_connection as get_banco_connection
from datetime import datetime, timezone
import os

client = TestClient(app)

def test_painel_sobrevive_ao_reiniciar_o_banco(monkeypatch, tmp_path):
    # Criar um novo banco SQLite e reiniciar a camada
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setattr("app.database.DB_PATH", str(db_path))
    monkeypatch.setattr("app.banco.get_backend_type", lambda: "sqlite_efemero")

    # Precisamos limpar qualquer global de initialized do banco pra garantir q cria certo
    import app.banco
    app.banco._db_initialized = False

    # Gravar o dado de teste
    agora = datetime.now(timezone.utc)
    save_apetite_risco_data(
        ApetiteRiscoData(
            timestamp=agora, estado="Risco on", diferenca=2.5, fonte="yfinance"
        )
    )

    # Fazer a requisição
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.text

    assert "Risco on" in html
    assert "2,5" in html
