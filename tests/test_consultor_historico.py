from unittest.mock import MagicMock
from app.collectors import consultor_historico


def test_consultor_historico_coleta(monkeypatch):
    mock_fetch = MagicMock()
    mock_fetch.return_value = {
        "symbol": "PETR4",
        "timestamp": [1600000000, 1600086400],
        "indicators": {"quote": [{"close": [10.0, 11.0], "volume": [100, 200]}]},
    }

    monkeypatch.setattr(
        "app.collectors.consultor_historico.fetch_historico_diario_yfinance_chart",
        mock_fetch,
    )

    sucesso = consultor_historico.collect_and_save()
    assert sucesso is True
    # Deveria ter chamado para cada ativo + IBOV
    assert mock_fetch.call_count > 0
