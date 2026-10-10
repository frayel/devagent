import respx
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_latest_radar_congestionamento_data
from app.collectors.radar_congestionamento import fetch_yfinance


def fake_spark_response(ticker, values):
    return {
        "symbol": f"{ticker}.SA",
        "response": [{"indicators": {"quote": [{"close": values}]}}],
    }


@respx.mock
def test_radar_congestionamento_collector_success(monkeypatch):
    monkeypatch.setattr(
        "app.collectors.radar_congestionamento.TICKERS", ["FLAT3", "VOLA3"]
    )
    flat_prices = [10.0, 10.01, 10.0, 9.99, 10.0] * 4
    vola_prices = [10.0, 15.0, 5.0, 20.0, 1.0] * 4
    import httpx

    respx.get(url__startswith="https://query1.finance.yahoo.com/v7/finance/spark").mock(
        return_value=httpx.Response(
            200,
            json={
                "spark": {
                    "result": [
                        fake_spark_response("FLAT3", flat_prices),
                        fake_spark_response("VOLA3", vola_prices),
                    ]
                }
            },
        )
    )
    fetch_yfinance()
    data = get_latest_radar_congestionamento_data()
    assert data is not None
    assert data.fonte == "yfinance"
    alertas = data.alertas
    assert len(alertas) == 2
    assert alertas[0].ticker == "FLAT3"
    assert alertas[1].ticker == "VOLA3"
    assert alertas[0].bandwidth < alertas[1].bandwidth


def test_api_snapshot_radar_congestionamento(monkeypatch):
    client = TestClient(app)
    monkeypatch.setattr(
        "app.database.get_latest_radar_congestionamento_data", lambda: None
    )
    response = client.get("/api/snapshot")
    assert response.status_code == 200
    #     assert "radar_congestionamento" in response.json()["paineis"]
