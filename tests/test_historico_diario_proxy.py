import json
import httpx
from datetime import datetime, timedelta, timezone
from app.database import save_historico_diario
from app.collectors.utils import fetch_historico_diario_yfinance_spark


def _bloco(simbolo: str, n: int = 10) -> dict:
    """Bloco de `chart.result[0]`, o formato que `save_historico_diario` grava."""
    ontem = datetime.now(timezone.utc).replace(
        hour=13, minute=0, second=0, microsecond=0
    ) - timedelta(days=1)
    return {
        "symbol": simbolo,
        "timestamp": [
            int((ontem - timedelta(days=n - 1 - i)).timestamp()) for i in range(n)
        ],
        "indicators": {"quote": [{"close": [30.0 + i for i in range(n)]}]},
    }


def test_fetch_historico_diario_uses_cache(monkeypatch):
    import app.database

    app.database.init_db()

    ticker = "PETR4"
    range_str = "1mo"
    interval = "1d"

    save_historico_diario(
        ticker,
        range_str,
        interval,
        json.dumps(_bloco(f"{ticker}.SA")),
        datetime.now(timezone.utc),
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


def test_fetch_historico_diario_fetches_missing(monkeypatch):
    import app.database

    app.database.init_db()

    cached_ticker = "VALE3"
    missing_ticker = "ITUB4"
    range_str = "1mo"
    interval = "1d"

    save_historico_diario(
        cached_ticker,
        range_str,
        interval,
        json.dumps(_bloco(f"{cached_ticker}.SA")),
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
            json={"spark": {"result": [_bloco("ITUB4.SA")]}},
        )

    monkeypatch.setattr("app.collectors.utils.fetch_with_retry", mock_fetch)

    client = httpx.Client()
    results = fetch_historico_diario_yfinance_spark(
        [cached_ticker, missing_ticker], range_str, interval, client
    )

    assert mock_called, "API was not hit for missing ticker"
    assert len(results) == 2
    symbols = [r["symbol"] for r in results]
    assert "ITUB4.SA" in symbols
