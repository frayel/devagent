import json

import httpx
import respx
import pytest

from app.collectors.volume_alerts import fetch_yfinance, collect_and_save
from app.database import get_latest_volume_alerts_data


@pytest.fixture(autouse=True)
def mock_tickers(monkeypatch):
    monkeypatch.setattr("app.collectors.volume_alerts.TICKERS", ["TICKER1", "TICKER2"])


@pytest.fixture
def mock_yfinance_spark():
    with respx.mock(assert_all_mocked=False) as respx_mock:
        # Mock the YF spark endpoint for any matching URL
        route = respx_mock.get(
            url__regex=r"https://query1\.finance\.yahoo\.com/v7/finance/spark\?symbols=.*"
        )

        # Create fake volumes: 21 days of normal volume (100) and today (last)
        # TICKER1: ratio > 1.5 (e.g. 250 vs 100 avg)
        # TICKER2: ratio < 1.5 (e.g. 120 vs 100 avg)

        volumes_t1 = [100] * 21 + [250]
        volumes_t2 = [100] * 21 + [120]
        timestamp = list(range(100000, 100000 + 22 * 86400, 86400))

        mock_data = {
            "spark": {
                "result": [
                    {
                        "symbol": "TICKER1.SA",
                        "response": [
                            {
                                "meta": {"regularMarketPrice": 15.5},
                                "timestamp": timestamp,
                                "indicators": {"quote": [{"volume": volumes_t1}]},
                            }
                        ],
                    },
                    {
                        "symbol": "TICKER2.SA",
                        "response": [
                            {
                                "meta": {"regularMarketPrice": 20.0},
                                "timestamp": timestamp,
                                "indicators": {"quote": [{"volume": volumes_t2}]},
                            }
                        ],
                    },
                ]
            }
        }

        route.return_value = httpx.Response(200, json=mock_data)
        yield respx_mock


def test_fetch_yfinance(mock_yfinance_spark):
    data = fetch_yfinance()
    assert data is not None
    assert data.fonte == "yfinance"

    alerts = json.loads(data.alerts_json)
    assert len(alerts) == 1

    # Check that only TICKER1 is included because ratio > 1.5
    assert alerts[0]["ticker"] == "TICKER1"
    assert alerts[0]["ratio"] == 2.5
    assert alerts[0]["price"] == 15.5


def test_collect_and_save(mock_yfinance_spark, setup_db):
    success = collect_and_save()
    assert success is True

    data = get_latest_volume_alerts_data()
    assert data is not None

    alerts = json.loads(data.alerts_json)
    assert len(alerts) == 1
    assert alerts[0]["ticker"] == "TICKER1"
