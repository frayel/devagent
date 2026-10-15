import json
from unittest.mock import Mock
from app.collectors.concentracao_ordens import collect_and_save
from app.database import get_latest_concentracao_ordens_data, init_db


def test_concentracao_ordens_sucesso(monkeypatch):
    init_db()
    mock_response = Mock()
    mock_response.json.return_value = {
        "results": [
            {
                "symbol": "PETR4",
                "regularMarketVolume": 1000,
                "regularMarketPrice": 30.0,
                "regularMarketTrades": 10,
            },
            {
                "symbol": "VALE3",
                "regularMarketVolume": 500,
                "regularMarketPrice": 60.0,
                "regularMarketTrades": 20,
            },
        ]
    }
    monkeypatch.setattr(
        "app.collectors.concentracao_ordens.fetch_with_retry", lambda url: mock_response
    )
    assert collect_and_save() is True
    data = get_latest_concentracao_ordens_data()
    assert data is not None
    assert data.fonte == "brapi"
    alertas = json.loads(data.alertas_json)
    assert len(alertas) == 2
    assert alertas[0]["ticker"] == "PETR4"
    assert alertas[0]["ticket_medio"] == 3000.0


def test_concentracao_ordens_sem_trades(monkeypatch):
    init_db()
    mock_response = Mock()
    mock_response.json.return_value = {
        "results": [
            {"symbol": "ITUB4", "regularMarketVolume": 1000, "regularMarketPrice": 30.0}
        ]
    }
    monkeypatch.setattr(
        "app.collectors.concentracao_ordens.fetch_with_retry", lambda url: mock_response
    )
    assert collect_and_save() is True
    data = get_latest_concentracao_ordens_data()
    assert data is not None
    alertas = json.loads(data.alertas_json)
    assert len(alertas) == 0
