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
    # 5 highs with distinct positive changes
    for i in range(5):
        results.append(
            {
                "symbol": f"HIGH{i}",
                "regularMarketPrice": 100.0 + i * 2,
                "regularMarketPreviousClose": 90.0,
            }
        )
    # 5 lows with distinct negative changes
    for i in range(5):
        results.append(
            {
                "symbol": f"LOW{i}",
                "regularMarketPrice": 80.0 - i * 2,
                "regularMarketPreviousClose": 90.0,
            }
        )
    return {"results": results}


def generate_mock_yfinance_data(ticker, is_high=False, multiplier=1):
    price = (100.0 + multiplier * 2) if is_high else (80.0 - multiplier * 2)
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
def test_fetch_brapi_success(monkeypatch):
    monkeypatch.setattr("app.collectors.utils.time.sleep", lambda s: None)
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

        # Validate order: largest positive change first
        assert highs[0]["change_percent"] > highs[1]["change_percent"]
        assert highs[1]["change_percent"] > highs[2]["change_percent"]
        assert highs[0]["ticker"] == "HIGH4"  # Largest variation: 108 vs 90

        # Validate order: largest negative change first (lowest percentage)
        assert lows[0]["change_percent"] < lows[1]["change_percent"]
        assert lows[1]["change_percent"] < lows[2]["change_percent"]
        assert lows[0]["ticker"] == "LOW4"  # Largest negative variation: 72 vs 90

        assert data.fonte == "brapi"


@respx.mock
def test_fetch_yfinance_success(monkeypatch):
    monkeypatch.setattr("app.collectors.utils.time.sleep", lambda s: None)
    for i, ticker in enumerate(TICKERS):
        is_high = i % 2 == 0
        yfinance_data = generate_mock_yfinance_data(ticker, is_high, i // 2)
        respx.get(
            f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}.SA?range=1d&interval=1d"
        ).respond(status_code=200, json=yfinance_data)

    data = fetch_yfinance()
    assert data is not None

    highs = json.loads(data.highs_json)
    lows = json.loads(data.lows_json)

    assert len(highs) == 5
    assert len(lows) == 5

    # Validate order
    assert highs[0]["change_percent"] > highs[1]["change_percent"]
    assert lows[0]["change_percent"] < lows[1]["change_percent"]
    assert data.fonte == "yfinance"


@respx.mock
def test_collect_and_save_fallback(monkeypatch):
    monkeypatch.setattr("app.collectors.utils.time.sleep", lambda s: None)
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
            yfinance_data = generate_mock_yfinance_data(ticker, is_high, i // 2)
            respx.get(
                f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}.SA?range=1d&interval=1d"
            ).respond(status_code=200, json=yfinance_data)

        success = collect_and_save()
        assert success is True

        db_data = get_latest_highlights_data()
        assert db_data is not None


@respx.mock
def test_index_route(monkeypatch):
    monkeypatch.setattr("app.collectors.utils.time.sleep", lambda s: None)
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
    assert "Fonte: brapi" in response.text


@respx.mock
def test_fetch_less_than_5_assets(monkeypatch):
    monkeypatch.setattr("app.collectors.utils.time.sleep", lambda s: None)
    brapi_data = {"results": []}

    # 3 assets total
    for i in range(3):
        brapi_data["results"].append(
            {
                "symbol": f"ASSET{i}",
                "regularMarketPrice": 100.0 + i * 2,
                "regularMarketPreviousClose": 90.0,
            }
        )

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
    assert "ASSET0" in response.text


@respx.mock
def test_index_route_yfinance(monkeypatch):
    monkeypatch.setattr("app.collectors.utils.time.sleep", lambda s: None)

    with mock.patch.dict(os.environ, {"BRAPI_TOKEN": "test_token"}):
        # Brapi fails
        tickers_str = ",".join(TICKERS)
        respx.get(
            httpx.URL(
                f"https://brapi.dev/api/quote/{tickers_str}?token=test_token&fundamental=false"
            )
        ).respond(status_code=500)

        # Yfinance succeeds
        for i, ticker in enumerate(TICKERS):
            is_high = i % 2 == 0
            yfinance_data = generate_mock_yfinance_data(ticker, is_high, i // 2)
            respx.get(
                f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}.SA?range=1d&interval=1d"
            ).respond(status_code=200, json=yfinance_data)

        collect_and_save()

    response = client.get("/")
    assert response.status_code == 200
    assert "Fonte: yfinance" in response.text
