import respx
import datetime
from datetime import timezone, timedelta
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_latest_detector_acao_orfa_data
from app.collectors.detector_acao_orfa import fetch_yfinance


def fake_spark_response(ticker, volumes):
    return {
        "symbol": f"{ticker}.SA",
        "response": [{"indicators": {"quote": [{"volume": volumes}]}}],
    }


@respx.mock
@patch("app.collectors.detector_acao_orfa.datetime")
def test_detector_acao_orfa_collector_success(mock_datetime, monkeypatch):
    mock_datetime.datetime.now.return_value = datetime.datetime(
        2026, 10, 12, 14, 0, tzinfo=timezone(timedelta(hours=-3))
    )
    monkeypatch.setattr(
        "app.collectors.detector_acao_orfa.TICKERS", ["VALE3", "PETR4", "ITUB4"]
    )

    # VALE3 normal (not orphan)
    vale_volumes = [1000, 2000, 1500, 1800, 1900]
    # PETR4 orphan (last volume 0)
    petr_volumes = [5000, 4000, 6000, 4500, 0]
    # ITUB4 orphan (last volume drop > 95%)
    itub_volumes = [1000, 1000, 1000, 1000, 10]

    import httpx

    respx.get(
        url__regex=r"https://query[12]\.finance\.yahoo\.com/v7/finance/spark.*"
    ).mock(
        return_value=httpx.Response(
            200,
            json={
                "spark": {
                    "result": [
                        fake_spark_response("VALE3", vale_volumes),
                        fake_spark_response("PETR4", petr_volumes),
                        fake_spark_response("ITUB4", itub_volumes),
                    ]
                }
            },
        )
    )

    fetch_yfinance()
    data = get_latest_detector_acao_orfa_data()
    assert data is not None
    assert data.fonte == "yfinance"
    alertas = data.alertas
    assert len(alertas) == 2
    tickers = [a.ticker for a in alertas]
    assert "PETR4" in tickers
    assert "ITUB4" in tickers
    assert "VALE3" not in tickers


def test_api_snapshot_detector_acao_orfa(monkeypatch):
    client = TestClient(app)
    monkeypatch.setattr("app.database.get_latest_detector_acao_orfa_data", lambda: None)
    response = client.get("/api/snapshot")
    assert response.status_code == 200
    assert "detector_acao_orfa" in response.json()["paineis"]
