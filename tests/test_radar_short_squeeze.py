import pytest
import respx
from httpx import Response
from app.collectors import radar_short_squeeze
from app.database import get_latest_radar_short_squeeze_data


@pytest.fixture
def mock_yfinance_spark():
    with respx.mock(assert_all_mocked=False) as respx_mock:
        route = respx_mock.get(
            url__startswith="https://query1.finance.yahoo.com/v7/finance/spark"
        )
        yield route


def test_radar_short_squeeze_success(mock_yfinance_spark, monkeypatch):
    monkeypatch.setattr("app.collectors.radar_short_squeeze.TICKERS", ["TEST3"])

    mock_data = {
        "spark": {
            "result": [
                {
                    "symbol": "TEST3.SA",
                    "response": [
                        {
                            "indicators": {
                                "quote": [
                                    {
                                        "close": [
                                            10.0,
                                            9.0,
                                            8.0,
                                            7.0,
                                            6.0,
                                            5.0,
                                            4.0,
                                            3.0,
                                            2.0,
                                            1.0,
                                            1.05,
                                        ],
                                        "volume": [
                                            100,
                                            100,
                                            100,
                                            100,
                                            100,
                                            100,
                                            100,
                                            100,
                                            100,
                                            100,
                                            300,
                                        ],
                                    }
                                ]
                            }
                        }
                    ],
                }
            ]
        }
    }
    mock_yfinance_spark.return_value = Response(200, json=mock_data)

    success = radar_short_squeeze.collect_and_save()
    assert success is True

    data = get_latest_radar_short_squeeze_data()
    assert data is not None
    alertas = __import__("json").loads(data.alertas_json)
    assert len(alertas) == 1
    assert alertas[0]["ticker"] == "TEST3"
    assert alertas[0]["mult_vol"] == 3.0
