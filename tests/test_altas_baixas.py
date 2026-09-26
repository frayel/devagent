import json
from datetime import datetime, timezone

import pytest
import respx

from app.collectors.altas_baixas import fetch_brapi, fetch_yfinance, TICKERS
from app.database import init_db, AltasBaixasData, save_altas_baixas_data
from app.services.altas_baixas import get_altas_baixas_view_data


@pytest.fixture(autouse=True)
def setup_db():
    init_db()


def test_fetch_brapi_success(monkeypatch):
    monkeypatch.setenv("BRAPI_TOKEN", "fake_token")

    mock_results = []
    # Create some mock data
    for i, ticker in enumerate(TICKERS[:10]):
        mock_results.append(
            {
                "symbol": ticker,
                "regularMarketPrice": 10.0 + i,
                "regularMarketPreviousClose": 10.0,  # Variations will be 0%, 10%, 20%, etc.
            }
        )

    mock_response = {"results": mock_results}

    tickers_str = ",".join(TICKERS)
    with respx.mock:
        respx.get(
            f"https://brapi.dev/api/quote/{tickers_str}?token=fake_token&fundamental=false"
        ).respond(json=mock_response)

        data = fetch_brapi()

        assert data is not None
        assert data.source == "brapi.dev"

        top_altas = json.loads(data.top_altas_json)
        assert len(top_altas) == 5
        assert (
            top_altas[0]["ticker"] == TICKERS[9]
        )  # Highest variation (19 vs 10 = +90%)

        top_baixas = json.loads(data.top_baixas_json)
        assert len(top_baixas) == 5
        assert top_baixas[0]["ticker"] == TICKERS[0]  # Lowest variation (10 vs 10 = 0%)


def test_fetch_yfinance_fallback():
    with respx.mock:
        for i, ticker in enumerate(TICKERS):
            # Create a mix of positive and negative variations
            price = 10.0 + (i - 5)  # Prices from 5.0 to 24.0
            prev_close = 10.0

            mock_response = {
                "chart": {
                    "result": [
                        {
                            "meta": {
                                "regularMarketPrice": price,
                                "chartPreviousClose": prev_close,
                            }
                        }
                    ]
                }
            }
            respx.get(
                f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}.SA?range=1d&interval=1d"
            ).respond(json=mock_response)

        data = fetch_yfinance()

        assert data is not None
        assert data.source == "Yahoo Finance"

        top_altas = json.loads(data.top_altas_json)
        assert len(top_altas) == 5
        assert top_altas[0]["ticker"] == TICKERS[-1]  # Highest price

        top_baixas = json.loads(data.top_baixas_json)
        assert len(top_baixas) == 5
        assert top_baixas[0]["ticker"] == TICKERS[0]  # Lowest price


def test_get_altas_baixas_view_data():
    mock_data = AltasBaixasData(
        timestamp=datetime(2023, 10, 26, 12, 0, tzinfo=timezone.utc),
        top_altas_json=json.dumps(
            [{"ticker": "PETR4", "price": 35.50, "variation_percent": 2.5}]
        ),
        top_baixas_json=json.dumps(
            [{"ticker": "VALE3.SA", "price": 60.10, "variation_percent": -1.2}]
        ),
        source="Test Source",
    )
    save_altas_baixas_data(mock_data)

    view_data = get_altas_baixas_view_data()

    assert view_data is not None
    assert view_data["source"] == "Test Source"
    assert view_data["time"] == "26/10/2023 12:00:00 UTC"

    assert len(view_data["top_altas"]) == 1
    alta = view_data["top_altas"][0]
    assert alta["ticker"] == "PETR4"
    assert alta["price"] == "35,50"
    assert alta["variation_percent"] == "+2.50%"
    assert alta["is_positive"] is True

    assert len(view_data["top_baixas"]) == 1
    baixa = view_data["top_baixas"][0]
    assert baixa["ticker"] == "VALE3"  # Should strip .SA
    assert baixa["price"] == "60,10"
    assert baixa["variation_percent"] == "-1.20%"
    assert baixa["is_negative"] is True
