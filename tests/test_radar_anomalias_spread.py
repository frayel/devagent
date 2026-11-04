import json
import os
from unittest import mock

import respx
from fastapi.testclient import TestClient

from app.collectors.radar_anomalias_spread import collect_and_save, CESTA_LIQUIDEZ
from app.database import get_latest_radar_anomalias_spread_data
from app.main import app

client = TestClient(app)


def generate_mock_brapi_data():
    results = []
    # Add one normal
    results.append(
        {
            "symbol": "NORM",
            "regularMarketDayHigh": 10.01,
            "regularMarketDayLow": 10.0,
            "regularMarketVolume": 100000,
        }
    )
    # Add one anomaly
    results.append(
        {
            "symbol": "PETR4",
            "regularMarketDayHigh": 10.10,
            "regularMarketDayLow": 10.0,
            "regularMarketVolume": 100000,
        }
    )
    return {"results": results}


@respx.mock
def test_fetch_brapi_success(monkeypatch):
    monkeypatch.setattr("app.collectors.utils.time.sleep", lambda s: None)
    brapi_data = generate_mock_brapi_data()
    ",".join(CESTA_LIQUIDEZ)

    with mock.patch.dict(os.environ, {"BRAPI_TOKEN": "test_token"}):
        import httpx

        def mock_brapi_router(request):
            symbol = request.url.path.split("/")[-1].split("?")[0]
            res_match = next(
                (res for res in brapi_data["results"] if res["symbol"] == symbol), None
            )
            if res_match:
                return httpx.Response(200, json={"results": [res_match]})
            return httpx.Response(
                200, json={"results": [{"symbol": symbol, "regularMarketPrice": 10.0}]}
            )

        respx.get(url__startswith="https://brapi.dev/api/quote/").mock(
            side_effect=mock_brapi_router
        )

        success = collect_and_save()
        assert success is True

        db_data = get_latest_radar_anomalias_spread_data()
        assert db_data is not None

        alertas = json.loads(db_data.alertas_json)
        assert len(alertas) == 1
        assert alertas[0]["ticker"] == "PETR4"
        assert abs(alertas[0]["spread_percent"] - 1.0) < 0.001


@respx.mock
def test_index_route(monkeypatch):
    monkeypatch.setattr("app.collectors.utils.time.sleep", lambda s: None)
    brapi_data = generate_mock_brapi_data()
    ",".join(CESTA_LIQUIDEZ)
    with mock.patch.dict(os.environ, {"BRAPI_TOKEN": "test_token"}):
        import httpx

        def mock_brapi_router(request):
            symbol = request.url.path.split("/")[-1].split("?")[0]
            res_match = next(
                (res for res in brapi_data["results"] if res["symbol"] == symbol), None
            )
            if res_match:
                return httpx.Response(200, json={"results": [res_match]})
            return httpx.Response(
                200, json={"results": [{"symbol": symbol, "regularMarketPrice": 10.0}]}
            )

        respx.get(url__startswith="https://brapi.dev/api/quote/").mock(
            side_effect=mock_brapi_router
        )

        collect_and_save()

    response = client.get("/")
    assert response.status_code == 200
    assert "Anomalias de Spread" in response.text
    assert "PETR4" in response.text


@respx.mock
def test_snapshot_route(monkeypatch):
    monkeypatch.setattr("app.collectors.utils.time.sleep", lambda s: None)
    brapi_data = generate_mock_brapi_data()
    ",".join(CESTA_LIQUIDEZ)
    with mock.patch.dict(os.environ, {"BRAPI_TOKEN": "test_token"}):
        import httpx

        def mock_brapi_router(request):
            symbol = request.url.path.split("/")[-1].split("?")[0]
            res_match = next(
                (res for res in brapi_data["results"] if res["symbol"] == symbol), None
            )
            if res_match:
                return httpx.Response(200, json={"results": [res_match]})
            return httpx.Response(
                200, json={"results": [{"symbol": symbol, "regularMarketPrice": 10.0}]}
            )

        respx.get(url__startswith="https://brapi.dev/api/quote/").mock(
            side_effect=mock_brapi_router
        )

        collect_and_save()

    response = client.get("/api/snapshot")
    assert response.status_code == 200
    data = response.json()
    assert "anomalias_spread" in data["paineis"]
    assert len(data["paineis"]["anomalias_spread"]) == 1
    assert data["paineis"]["anomalias_spread"][0]["ticker"] == "PETR4"
