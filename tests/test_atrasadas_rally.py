import json
import pytest
import httpx
import respx
from app.collectors import atrasadas_rally
from app.database import init_db


@pytest.fixture(autouse=True)
def test_db(monkeypatch, tmp_path):
    db_file = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_PATH", str(db_file))
    init_db()


@respx.mock
def test_fetch_atrasadas_rally_valido():
    mock_data = {
        "spark": {
            "result": [
                {
                    "symbol": "^BVSP",
                    "response": [
                        {
                            "indicators": {
                                "quote": [
                                    {"close": [100.0, 101.0, 102.0, 103.0, 104.0]}
                                ]
                            }
                        }
                    ],
                },
                {
                    "symbol": "VALE3.SA",
                    "response": [
                        {
                            "indicators": {
                                "quote": [{"close": [50.0, 50.5, 49.0, 48.0, 49.0]}]
                            }
                        }
                    ],
                },
            ]
        }
    }
    respx.get(url__startswith="https://query1.finance.yahoo.com/v7/finance/spark").mock(
        return_value=httpx.Response(200, json=mock_data)
    )

    data = atrasadas_rally.fetch_yfinance()
    assert data is not None
    assert data.rally_valido is True
    top3 = json.loads(data.top3_json)
    assert len(top3) == 1
    assert top3[0]["ticker"] == "VALE3"
    assert "retorno" in top3[0]


@respx.mock
def test_fetch_atrasadas_rally_invalido():
    mock_data = {
        "spark": {
            "result": [
                {
                    "symbol": "^BVSP",
                    "response": [
                        {
                            "indicators": {
                                "quote": [
                                    {"close": [100.0, 100.5, 100.8, 101.0, 101.5]}
                                ]
                            }
                        }
                    ],
                }
            ]
        }
    }
    respx.get(url__startswith="https://query1.finance.yahoo.com/v7/finance/spark").mock(
        return_value=httpx.Response(200, json=mock_data)
    )

    data = atrasadas_rally.fetch_yfinance()
    assert data is not None
    assert data.rally_valido is False
