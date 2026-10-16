import json
import httpx
from datetime import datetime, timezone
from app.database import save_historico_diario
from app.collectors.utils import fetch_historico_diario_yfinance_spark


def test_fetch_historico_diario_uses_cache(monkeypatch):
    import app.database

    app.database.init_db()

    ticker = "PETR4"
    range_str = "10d"
    interval = "1d"
    fake_data = {"symbol": f"{ticker}.SA", "response": [{"meta": {"test": True}}]}

    save_historico_diario(
        ticker, range_str, interval, json.dumps(fake_data), datetime.now(timezone.utc)
    )

    mock_called = False

    def mock_fetch(*args, **kwargs):
        nonlocal mock_called
        mock_called = True
        return httpx.Response(200, json={"spark": {"result": []}})

    monkeypatch.setattr("app.collectors.utils.fetch_with_retry", mock_fetch)

    client = httpx.Client()
    results = fetch_historico_diario_yfinance_spark(
        [ticker], range_str, interval, client
    )

    assert not mock_called, "API was hit even though data was in cache"
    assert len(results) == 1
    assert results[0]["symbol"] == "PETR4.SA"


def test_fetch_historico_diario_fetches_missing(monkeypatch):
    import app.database

    app.database.init_db()

    cached_ticker = "VALE3"
    missing_ticker = "ITUB4"
    range_str = "10d"
    interval = "1d"

    fake_cached_data = {
        "symbol": f"{cached_ticker}.SA",
        "response": [{"meta": {"test": True}}],
    }
    save_historico_diario(
        cached_ticker,
        range_str,
        interval,
        json.dumps(fake_cached_data),
        datetime.now(timezone.utc),
    )

    mock_called = False

    def mock_fetch(url, *args, **kwargs):
        nonlocal mock_called
        mock_called = True
        assert "ITUB4.SA" in url
        assert "VALE3.SA" not in url
        return httpx.Response(
            200,
            json={
                "spark": {
                    "result": [
                        {"symbol": "ITUB4.SA", "response": [{"meta": {"test2": True}}]}
                    ]
                }
            },
        )

    monkeypatch.setattr("app.collectors.utils.fetch_with_retry", mock_fetch)

    client = httpx.Client()
    results = fetch_historico_diario_yfinance_spark(
        [cached_ticker, missing_ticker], range_str, interval, client
    )

    assert mock_called, "API was not hit for missing ticker"
    assert len(results) == 2
    symbols = [r["symbol"] for r in results]
    assert "VALE3.SA" in symbols
    assert "ITUB4.SA" in symbols
