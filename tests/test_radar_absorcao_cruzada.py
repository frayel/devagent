import json
from datetime import datetime, timezone

from app.database import (
    RadarAbsorcaoCruzadaData,
    get_latest_radar_absorcao_cruzada_data,
    init_db,
    save_radar_absorcao_cruzada_data,
)
from app.collectors.radar_absorcao_cruzada import fetch_yfinance, collect_and_save


def test_save_and_get_radar_absorcao_cruzada(setup_db):
    init_db()
    data = RadarAbsorcaoCruzadaData(
        timestamp=datetime(2023, 1, 1, 10, 0, tzinfo=timezone.utc),
        alertas_json=json.dumps([{"ticker": "VALE3", "ratio": 2.5, "drop_pct": -2.0}]),
        fonte="test",
    )
    save_radar_absorcao_cruzada_data(data)

    latest = get_latest_radar_absorcao_cruzada_data()
    assert latest is not None
    assert latest.fonte == "test"

    alertas = json.loads(latest.alertas_json)
    assert len(alertas) == 1
    assert alertas[0]["ticker"] == "VALE3"


def test_fetch_yfinance_success(respx_mock, monkeypatch):
    monkeypatch.setattr(
        "app.collectors.radar_absorcao_cruzada.TICKERS", ["VALE3", "PETR4"]
    )
    respx_mock.get(
        "https://query1.finance.yahoo.com/v8/finance/chart/PETR4.SA?range=5d&interval=15m"
    ).respond(status_code=404)

    # We need timestamps that span multiple days.
    # Let's say day 1 is timestamp 1600000000 and day 2 is 1600086400
    t1 = 1600000000
    t2 = 1600086400

    chart_data = {
        "chart": {
            "result": [
                {
                    "meta": {"symbol": "VALE3.SA"},
                    "timestamp": [
                        t1,
                        t1 + 900,
                        t1 + 1800,
                        t1 + 2700,
                        t1 + 3600,
                        t1 + 4500,
                        t1 + 5400,
                        t1 + 6300,
                        t1 + 7200,
                        t1 + 8100,  # Previous day (10 candles)
                        t2,
                        t2 + 900,
                        t2 + 1800,  # Current day (3 candles)
                    ],
                    "indicators": {
                        "quote": [
                            {
                                # Prev day: all down-candles (close < open), volume = 1M
                                "open": [100.0] * 10 + [98.0, 97.0, 96.0],
                                "high": [100.0] * 10 + [98.0, 97.0, 96.0],
                                "low": [90.0] * 10
                                + [
                                    97.0,
                                    96.0,
                                    92.0,
                                ],  # Min low current day is 92.0 (last candle)
                                "close": [95.0] * 10
                                + [
                                    97.0,
                                    96.0,
                                    93.0,
                                ],  # Prev close = 95.0, Curr close = 93.0 (-2.1%)
                                "volume": [1000000] * 10
                                + [
                                    500000,
                                    600000,
                                    3000000,
                                ],  # Last candle has 3M volume. Ratio = 3.0
                            }
                        ]
                    },
                }
            ]
        }
    }

    respx_mock.get(
        "https://query1.finance.yahoo.com/v8/finance/chart/VALE3.SA?range=5d&interval=15m"
    ).respond(json=chart_data)

    result = fetch_yfinance()
    assert result is not None
    assert result.fonte == "yfinance"

    alertas = json.loads(result.alertas_json)
    assert len(alertas) == 1
    assert alertas[0]["ticker"] == "VALE3"
    assert alertas[0]["ratio"] == 3.0
    assert round(alertas[0]["drop_pct"], 1) == -2.1


def test_collect_and_save_success(respx_mock, monkeypatch, setup_db):
    init_db()
    monkeypatch.setattr("app.collectors.radar_absorcao_cruzada.TICKERS", ["VALE3"])
    t1 = 1600000000
    t2 = 1600086400
    chart_data = {
        "chart": {
            "result": [
                {
                    "meta": {"symbol": "VALE3.SA"},
                    "timestamp": [
                        t1,
                        t1 + 900,
                        t1 + 1800,
                        t1 + 2700,
                        t1 + 3600,
                        t1 + 4500,
                        t1 + 5400,
                        t1 + 6300,
                        t1 + 7200,
                        t1 + 8100,
                        t2,
                        t2 + 900,
                        t2 + 1800,
                    ],
                    "indicators": {
                        "quote": [
                            {
                                "open": [100.0] * 10 + [98.0, 97.0, 96.0],
                                "high": [100.0] * 10 + [98.0, 97.0, 96.0],
                                "low": [90.0] * 10 + [97.0, 96.0, 92.0],
                                "close": [95.0] * 10 + [97.0, 96.0, 93.0],
                                "volume": [1000000] * 10 + [500000, 600000, 3000000],
                            }
                        ]
                    },
                }
            ]
        }
    }

    respx_mock.get(
        "https://query1.finance.yahoo.com/v8/finance/chart/VALE3.SA?range=5d&interval=15m"
    ).respond(json=chart_data)

    assert collect_and_save() is True

    latest = get_latest_radar_absorcao_cruzada_data()
    assert latest is not None
    alertas = json.loads(latest.alertas_json)
    assert len(alertas) == 1
    assert alertas[0]["ticker"] == "VALE3"
