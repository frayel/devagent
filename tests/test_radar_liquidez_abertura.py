import json
from datetime import datetime, timezone

from app.database import (
    LiquidezAberturaData,
    get_latest_liquidez_abertura_data,
    init_db,
    save_liquidez_abertura_data,
)
from app.collectors.radar_liquidez_abertura import fetch_yfinance, collect_and_save


def test_save_and_get_liquidez_abertura(setup_db):
    init_db()
    data = LiquidezAberturaData(
        timestamp=datetime(2023, 1, 1, 10, 0, tzinfo=timezone.utc),
        alertas_json=json.dumps([{"ticker": "VALE3", "ratio": 1.5, "var_pct": 2.5}]),
        fonte="test",
    )
    save_liquidez_abertura_data(data)

    latest = get_latest_liquidez_abertura_data()
    assert latest is not None
    assert latest.fonte == "test"

    alertas = json.loads(latest.alertas_json)
    assert len(alertas) == 1
    assert alertas[0]["ticker"] == "VALE3"


def test_fetch_yfinance_success(respx_mock, monkeypatch):
    monkeypatch.setattr(
        "app.collectors.radar_liquidez_abertura.TICKERS", ["VALE3", "PETR4"]
    )
    respx_mock.get(
        "https://query1.finance.yahoo.com/v8/finance/chart/PETR4.SA?range=1mo&interval=1d"
    ).respond(status_code=404)

    chart_data = {
        "chart": {
            "result": [
                {
                    "meta": {"symbol": "VALE3.SA"},
                    "timestamp": list(range(100, 111)),  # 11 data points
                    "indicators": {
                        "quote": [
                            {
                                "volume": [1000000] * 10
                                + [
                                    2000000
                                ],  # Last volume is 2M, avg is 1M. Ratio = 2.0
                                "close": [50.0] * 10
                                + [55.0],  # Close increased from 50 to 55 (+10%)
                            }
                        ]
                    },
                }
            ]
        }
    }

    respx_mock.get(
        "https://query1.finance.yahoo.com/v8/finance/chart/VALE3.SA?range=1mo&interval=1d"
    ).respond(json=chart_data)

    result = fetch_yfinance()
    assert result is not None
    assert result.fonte == "yfinance"

    alertas = json.loads(result.alertas_json)
    assert len(alertas) == 1
    assert alertas[0]["ticker"] == "VALE3"
    assert alertas[0]["ratio"] == 2.0
    assert round(alertas[0]["var_pct"], 5) == 10.0


def test_collect_and_save_success(respx_mock, monkeypatch, setup_db):
    init_db()
    monkeypatch.setattr(
        "app.collectors.radar_liquidez_abertura.TICKERS", ["VALE3", "PETR4"]
    )
    respx_mock.get(
        "https://query1.finance.yahoo.com/v8/finance/chart/PETR4.SA?range=1mo&interval=1d"
    ).respond(status_code=404)

    chart_data = {
        "chart": {
            "result": [
                {
                    "meta": {"symbol": "VALE3.SA"},
                    "timestamp": list(range(100, 111)),
                    "indicators": {
                        "quote": [
                            {
                                "volume": [1000000] * 10 + [2000000],
                                "close": [50.0] * 10 + [55.0],
                            }
                        ]
                    },
                }
            ]
        }
    }

    respx_mock.get(
        "https://query1.finance.yahoo.com/v8/finance/chart/VALE3.SA?range=1mo&interval=1d"
    ).respond(json=chart_data)

    assert collect_and_save() is True

    latest = get_latest_liquidez_abertura_data()
    assert latest is not None
    alertas = json.loads(latest.alertas_json)
    assert len(alertas) == 1
    assert alertas[0]["ticker"] == "VALE3"
