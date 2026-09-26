import json
import os
from unittest import mock

import httpx
import respx
from fastapi.testclient import TestClient

from app.collectors.ibovespa import collect_and_save, fetch_brapi, fetch_yfinance
from app.database import get_latest_ibovespa_data
from app.main import app

import subprocess

client = TestClient(app)


def test_data_db_not_in_git():
    # Run git ls-files to ensure data.db is not tracked
    result = subprocess.run(
        ["git", "ls-files", "data.db"], capture_output=True, text=True, check=True
    )
    assert result.stdout.strip() == "", "data.db should not be tracked by git"


def load_fixture(name):
    with open(f"tests/fixtures/{name}") as f:
        return json.load(f)


@respx.mock
def test_fetch_brapi_success():
    brapi_data = load_fixture("brapi_response.json")
    with mock.patch.dict(os.environ, {"BRAPI_TOKEN": "test_token"}):
        respx.get(
            httpx.URL(
                "https://brapi.dev/api/quote/^BVSP?token=test_token&range=1mo&interval=1d&fundamental=false"
            )
        ).respond(status_code=200, json=brapi_data)
        data = fetch_brapi()
        assert data is not None
        assert data.current_price == 130000.5
        assert data.previous_close == 129000.0
        assert data.fonte == "brapi"


@respx.mock
def test_fetch_yfinance_success():
    yfinance_data = load_fixture("yfinance_response.json")
    respx.get(
        "https://query2.finance.yahoo.com/v8/finance/chart/^BVSP?range=1mo&interval=1d"
    ).respond(status_code=200, json=yfinance_data)
    data = fetch_yfinance()
    assert data is not None
    assert data.current_price == 131000.0
    assert data.previous_close == 132000.0
    assert data.fonte == "yfinance"


@respx.mock
def test_collect_and_save_fallback():
    # Brapi fails, yfinance succeeds
    yfinance_data = load_fixture("yfinance_response.json")
    with mock.patch.dict(os.environ, {"BRAPI_TOKEN": "test_token"}):
        respx.get(
            httpx.URL(
                "https://brapi.dev/api/quote/^BVSP?token=test_token&range=1mo&interval=1d&fundamental=false"
            )
        ).respond(status_code=500)
        respx.get(
            "https://query2.finance.yahoo.com/v8/finance/chart/^BVSP?range=1mo&interval=1d"
        ).respond(status_code=200, json=yfinance_data)

        success = collect_and_save()
        assert success is True

        db_data = get_latest_ibovespa_data()
        assert db_data is not None
        assert db_data.current_price == 131000.0
        assert db_data.previous_close == 132000.0
        assert db_data.fonte == "yfinance"


@respx.mock
def test_index_route():
    # Test when DB has no data
    response = client.get("/")
    assert response.status_code == 200
    assert "Dados não disponíveis no momento" in response.text

    # Add data to DB
    brapi_data = load_fixture("brapi_response.json")
    with mock.patch.dict(os.environ, {"BRAPI_TOKEN": "test_token"}):
        respx.get(
            httpx.URL(
                "https://brapi.dev/api/quote/^BVSP?token=test_token&range=1mo&interval=1d&fundamental=false"
            )
        ).respond(status_code=200, json=brapi_data)
        collect_and_save()

    response = client.get("/")
    assert response.status_code == 200
    assert "130.000 pontos" in response.text
    assert "+1.000 (+0.78%)" in response.text
