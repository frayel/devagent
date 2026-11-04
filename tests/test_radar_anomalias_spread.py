import json

import respx
from fastapi.testclient import TestClient

from app.collectors.radar_anomalias_spread import collect_and_save
from app.database import get_latest_radar_anomalias_spread_data
from app.main import app

client = TestClient(app)

SPARK = r"https://query[12]\.finance\.yahoo\.com/v8/finance/spark.*"


def _item(symbol: str, high: float, low: float) -> dict:
    return {
        "symbol": f"{symbol}.SA",
        "response": [
            {
                "meta": {
                    "regularMarketDayHigh": high,
                    "regularMarketDayLow": low,
                    "regularMarketVolume": 100000,
                }
            }
        ],
    }


def _spark() -> dict:
    # Uma ação normal (spread 0,1%) e uma anômala (spread 1%).
    return {
        "spark": {
            "result": [_item("NORM", 10.01, 10.0), _item("PETR4", 10.10, 10.0)],
            "error": None,
        }
    }


def _coletar(monkeypatch) -> None:
    monkeypatch.setattr("app.collectors.utils.time.sleep", lambda s: None)
    respx.get(url__regex=SPARK).respond(200, json=_spark())
    assert collect_and_save() is True


@respx.mock
def test_coleta_pelo_yahoo(monkeypatch):
    _coletar(monkeypatch)

    db_data = get_latest_radar_anomalias_spread_data()
    assert db_data is not None
    assert db_data.fonte == "yfinance"
    alertas = json.loads(db_data.alertas_json)
    assert len(alertas) == 1
    assert alertas[0]["ticker"] == "PETR4"
    assert abs(alertas[0]["spread_percent"] - 1.0) < 0.001


@respx.mock
def test_index_route(monkeypatch):
    _coletar(monkeypatch)

    response = client.get("/")
    assert response.status_code == 200
    assert "Anomalias de Spread" in response.text
    assert "PETR4" in response.text


@respx.mock
def test_snapshot_route(monkeypatch):
    _coletar(monkeypatch)

    response = client.get("/api/snapshot")
    assert response.status_code == 200
    data = response.json()
    assert "anomalias_spread" in data["paineis"]
    assert len(data["paineis"]["anomalias_spread"]) == 1
    assert data["paineis"]["anomalias_spread"][0]["ticker"] == "PETR4"
