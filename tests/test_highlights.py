import re
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
        "spark": {
            "result": [
                {
                    "symbol": f"{ticker}.SA",
                    "response": [
                        {
                            "meta": {
                                "regularMarketPrice": price,
                                "chartPreviousClose": 90.0,
                            }
                        }
                    ],
                }
            ]
        }
    }


def generate_mock_yfinance_batch_data(batch_tickers, global_offset=0):
    results = []
    for i, ticker in enumerate(batch_tickers):
        idx = global_offset + i
        is_high = idx % 2 == 0
        multiplier = idx // 2
        price = (100.0 + multiplier * 2) if is_high else (80.0 - multiplier * 2)
        results.append(
            {
                "symbol": f"{ticker}.SA",
                "response": [
                    {
                        "meta": {
                            "regularMarketPrice": price,
                            "chartPreviousClose": 90.0,
                        }
                    }
                ],
            }
        )
    return {"spark": {"result": results}}


@respx.mock
def test_fetch_brapi_success(monkeypatch):
    monkeypatch.setattr(
        "app.collectors.highlights.TICKERS",
        [f"HIGH{i}" for i in range(5)] + [f"LOW{i}" for i in range(5)],
    )
    monkeypatch.setattr("app.collectors.utils.time.sleep", lambda s: None)
    brapi_data = generate_mock_brapi_data()
    ",".join(TICKERS)
    with mock.patch.dict(os.environ, {"BRAPI_TOKEN": "test_token"}):
        import httpx

        def mock_brapi_router(request):
            symbol = request.url.path.split("/")[-1].split("?")[0]
            if symbol == "list":
                stocks = [
                    {
                        "stock": res["symbol"],
                        "change": (
                            res.get("regularMarketPrice", 10.0)
                            - res.get("regularMarketPreviousClose", 90.0)
                        )
                        / res.get("regularMarketPreviousClose", 90.0)
                        * 100,
                        "close": res.get("regularMarketPrice", 10.0),
                        "type": "stock",
                    }
                    for res in brapi_data["results"]
                ]
                return httpx.Response(200, json={"stocks": stocks})

            res_match = next(
                (res for res in brapi_data["results"] if res["symbol"] == symbol), None
            )
            if res_match:
                return httpx.Response(200, json={"results": [res_match]})
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "symbol": symbol,
                            "regularMarketPrice": 10.0,
                            "regularMarketPreviousClose": 10.0,
                        }
                    ]
                },
            )

        respx.get(url__startswith="https://brapi.dev/api/quote/").mock(
            side_effect=mock_brapi_router
        )

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
        assert data.up_count == 5
        assert data.down_count == 5
        assert data.total_count == 10


@respx.mock
def test_fetch_yfinance_success(monkeypatch):
    monkeypatch.setattr("app.collectors.utils.time.sleep", lambda s: None)

    batch_size = 15
    batches = [TICKERS[i : i + batch_size] for i in range(0, len(TICKERS), batch_size)]
    for batch_idx, batch in enumerate(batches):
        symbols = ",".join([f"{t}.SA" for t in batch])
        yfinance_data = generate_mock_yfinance_batch_data(
            batch, global_offset=batch_idx * batch_size
        )
        respx.get(
            re.compile(
                rf"https://query[12]\.finance\.yahoo\.com/v8/finance/spark\?symbols={symbols}&range=15d&interval=1d"
            )
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
    assert data.up_count == 15
    assert data.down_count == 15
    assert data.total_count == 30


@respx.mock
def test_collect_and_save_fallback(monkeypatch):
    monkeypatch.setattr("app.collectors.utils.time.sleep", lambda s: None)
    tickers_str = ",".join(TICKERS)
    with mock.patch.dict(os.environ, {"BRAPI_TOKEN": "test_token"}):
        # Brapi fails
        respx.get(
            httpx.URL(
                f"https://brapi.dev/api/quote/{tickers_str}?range=1mo&interval=1d&token=test_token&fundamental=false"
            )
        ).respond(status_code=500)

        # Brapi list fails too
        respx.get(url__startswith="https://brapi.dev/api/quote/list").respond(
            status_code=500
        )

        # Yfinance succeeds
        batch_size = 15
        batches = [
            TICKERS[i : i + batch_size] for i in range(0, len(TICKERS), batch_size)
        ]
        for batch_idx, batch in enumerate(batches):
            symbols = ",".join([f"{t}.SA" for t in batch])
            yfinance_data = generate_mock_yfinance_batch_data(
                batch, global_offset=batch_idx * batch_size
            )
            respx.get(
                re.compile(
                    rf"https://query[12]\.finance\.yahoo\.com/v8/finance/spark\?symbols={symbols}&range=15d&interval=1d"
                )
            ).respond(status_code=200, json=yfinance_data)

        success = collect_and_save()
        assert success is True

        db_data = get_latest_highlights_data()
        assert db_data is not None


@respx.mock
def test_index_route(monkeypatch):
    monkeypatch.setattr(
        "app.collectors.highlights.TICKERS",
        [f"HIGH{i}" for i in range(5)] + [f"LOW{i}" for i in range(5)],
    )
    monkeypatch.setattr("app.collectors.utils.time.sleep", lambda s: None)
    # Setup Brapi Mock and collect to have data in DB
    brapi_data = generate_mock_brapi_data()
    ",".join(TICKERS)
    with mock.patch.dict(os.environ, {"BRAPI_TOKEN": "test_token"}):
        import httpx

        def mock_brapi_router(request):
            symbol = request.url.path.split("/")[-1].split("?")[0]
            if symbol == "list":
                stocks = [
                    {
                        "stock": res["symbol"],
                        "change": (
                            res.get("regularMarketPrice", 10.0)
                            - res.get("regularMarketPreviousClose", 90.0)
                        )
                        / res.get("regularMarketPreviousClose", 90.0)
                        * 100,
                        "close": res.get("regularMarketPrice", 10.0),
                        "type": "stock",
                    }
                    for res in brapi_data["results"]
                ]
                return httpx.Response(200, json={"stocks": stocks})

            res_match = next(
                (res for res in brapi_data["results"] if res["symbol"] == symbol), None
            )
            if res_match:
                return httpx.Response(200, json={"results": [res_match]})
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "symbol": symbol,
                            "regularMarketPrice": 10.0,
                            "regularMarketPreviousClose": 10.0,
                        }
                    ]
                },
            )

        respx.get(url__startswith="https://brapi.dev/api/quote/").mock(
            side_effect=mock_brapi_router
        )
        collect_and_save()

    response = client.get("/")
    assert response.status_code == 200
    assert "Maiores altas" in response.text
    assert "Maiores baixas" in response.text
    assert "HIGH0" in response.text
    assert "LOW0" in response.text
    assert "Fonte brapi" in response.text
    assert "Dispersão" in response.text
    assert "5 subiram</span>" in response.text


@respx.mock
def test_fetch_less_than_5_assets(monkeypatch):
    monkeypatch.setattr(
        "app.collectors.highlights.TICKERS", [f"ASSET{i}" for i in range(3)]
    )
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

    ",".join(TICKERS)
    with mock.patch.dict(os.environ, {"BRAPI_TOKEN": "test_token"}):
        import httpx

        def mock_brapi_router(request):
            symbol = request.url.path.split("/")[-1].split("?")[0]
            if symbol == "list":
                stocks = [
                    {
                        "stock": res["symbol"],
                        "change": (
                            res.get("regularMarketPrice", 10.0)
                            - res.get("regularMarketPreviousClose", 90.0)
                        )
                        / res.get("regularMarketPreviousClose", 90.0)
                        * 100,
                        "close": res.get("regularMarketPrice", 10.0),
                        "type": "stock",
                    }
                    for res in brapi_data["results"]
                ]
                return httpx.Response(200, json={"stocks": stocks})

            res_match = next(
                (res for res in brapi_data["results"] if res["symbol"] == symbol), None
            )
            if res_match:
                return httpx.Response(200, json={"results": [res_match]})
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "symbol": symbol,
                            "regularMarketPrice": 10.0,
                            "regularMarketPreviousClose": 10.0,
                        }
                    ]
                },
            )

        respx.get(url__startswith="https://brapi.dev/api/quote/").mock(
            side_effect=mock_brapi_router
        )

        collect_and_save()

    response = client.get("/")
    assert response.status_code == 200
    assert "ASSET0" in response.text
    assert "Dispersão" in response.text
    assert "3 subiram</span>" in response.text


@respx.mock
def test_index_route_yfinance(monkeypatch):
    monkeypatch.setattr("app.collectors.utils.time.sleep", lambda s: None)

    with mock.patch.dict(os.environ, {"BRAPI_TOKEN": "test_token"}):
        # Brapi fails
        tickers_str = ",".join(TICKERS)
        respx.get(
            httpx.URL(
                f"https://brapi.dev/api/quote/{tickers_str}?range=1mo&interval=1d&token=test_token&fundamental=false"
            )
        ).respond(status_code=500)

        # Brapi list fails too
        respx.get(url__startswith="https://brapi.dev/api/quote/list").respond(
            status_code=500
        )

        # Yfinance succeeds
        batch_size = 15
        batches = [
            TICKERS[i : i + batch_size] for i in range(0, len(TICKERS), batch_size)
        ]
        for batch_idx, batch in enumerate(batches):
            symbols = ",".join([f"{t}.SA" for t in batch])
            yfinance_data = generate_mock_yfinance_batch_data(
                batch, global_offset=batch_idx * batch_size
            )
            respx.get(
                re.compile(
                    rf"https://query[12]\.finance\.yahoo\.com/v8/finance/spark\?symbols={symbols}&range=15d&interval=1d"
                )
            ).respond(status_code=200, json=yfinance_data)

        collect_and_save()

    response = client.get("/")
    assert response.status_code == 200
    assert "Fonte yfinance" in response.text
    assert "Dispersão" in response.text
    assert "15 subiram</span>" in response.text
