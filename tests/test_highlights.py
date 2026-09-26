import json
import os
from unittest import mock

import httpx
import respx
from fastapi.testclient import TestClient

from app.collectors.highlights import (
    TICKERS,
    collect_and_save,
    fetch_brapi,
    fetch_yfinance,
)
from app.database import get_latest_highlights_data
from app.main import app

client = TestClient(app)


def generate_mock_brapi_data():
    results = []
    # 5 highs
    for i in range(5):
        results.append(
            {
                "symbol": f"HIGH{i}",
                "regularMarketPrice": 100.0,
                "regularMarketPreviousClose": 90.0,  # ~11% change
            }
        )
    # 5 lows
    for i in range(5):
        results.append(
            {
                "symbol": f"LOW{i}",
                "regularMarketPrice": 80.0,
                "regularMarketPreviousClose": 90.0,  # ~-11% change
            }
        )
    return {"results": results}


def generate_mock_yfinance_data(ticker, is_high=False):
    price = 100.0 if is_high else 80.0
    return {
        "chart": {
            "result": [
                {
                    "meta": {
                        "regularMarketPrice": price,
                        "chartPreviousClose": 90.0,
                    }
                }
            ]
        }
    }


@respx.mock
def test_fetch_brapi_success():
    brapi_data = generate_mock_brapi_data()
    tickers_str = ",".join(TICKERS)
    with mock.patch.dict(os.environ, {"BRAPI_TOKEN": "test_token"}):
        respx.get(
            httpx.URL(
                f"https://brapi.dev/api/quote/{tickers_str}?token=test_token&fundamental=false"
            )
        ).respond(status_code=200, json=brapi_data)

        data = fetch_brapi()
        assert data is not None

        highs = json.loads(data.highs_json)
        lows = json.loads(data.lows_json)

        assert len(highs) == 5
        assert len(lows) == 5
        assert highs[0]["change_percent"] > 0
        assert lows[0]["change_percent"] < 0


@respx.mock
def test_fetch_yfinance_success():
    for i, ticker in enumerate(TICKERS):
        is_high = i % 2 == 0
        yfinance_data = generate_mock_yfinance_data(ticker, is_high)
        respx.get(
            f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}.SA?range=1d&interval=1d"
        ).respond(status_code=200, json=yfinance_data)

    data = fetch_yfinance()
    assert data is not None

    highs = json.loads(data.highs_json)
    lows = json.loads(data.lows_json)

    assert len(highs) == 5
    assert len(lows) == 5


@respx.mock
def test_collect_and_save_fallback():
    tickers_str = ",".join(TICKERS)
    with mock.patch.dict(os.environ, {"BRAPI_TOKEN": "test_token"}):
        # Brapi fails
        respx.get(
            httpx.URL(
                f"https://brapi.dev/api/quote/{tickers_str}?token=test_token&fundamental=false"
            )
        ).respond(status_code=500)

        # Yfinance succeeds
        for i, ticker in enumerate(TICKERS):
            is_high = i % 2 == 0
            yfinance_data = generate_mock_yfinance_data(ticker, is_high)
            respx.get(
                f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}.SA?range=1d&interval=1d"
            ).respond(status_code=200, json=yfinance_data)

        success = collect_and_save()
        assert success is True

        db_data = get_latest_highlights_data()
        assert db_data is not None


@respx.mock
def test_index_route():
    # Setup Brapi Mock and collect to have data in DB
    brapi_data = generate_mock_brapi_data()
    tickers_str = ",".join(TICKERS)
    with mock.patch.dict(os.environ, {"BRAPI_TOKEN": "test_token"}):
        respx.get(
            httpx.URL(
                f"https://brapi.dev/api/quote/{tickers_str}?token=test_token&fundamental=false"
            )
        ).respond(status_code=200, json=brapi_data)
        collect_and_save()

    response = client.get("/")
    assert response.status_code == 200
    assert "Maiores Altas" in response.text
    assert "Maiores Baixas" in response.text
    assert "HIGH0" in response.text
    assert "LOW0" in response.text
