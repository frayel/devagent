import pytest
from app.collectors.dolar_correlation import collect_and_save
from app.database import get_latest_dolar_correlation_data, init_db
import respx
import json


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    db_file = tmp_path / "test_dolar.db"
    monkeypatch.setenv("DATABASE_PATH", str(db_file))
    monkeypatch.setattr("app.database.DB_PATH", str(db_file))
    init_db()
    yield


@respx.mock
def test_collect_and_save_success(isolated_db, monkeypatch):
    # Mock dollar
    respx.get(
        url__startswith="https://query1.finance.yahoo.com/v7/finance/spark?symbols=BRL=X"
    ).respond(
        json={
            "spark": {
                "result": [
                    {
                        "response": [
                            {
                                "timestamp": list(range(30)),
                                "indicators": {"quote": [{"close": [5.0] * 30}]},
                            }
                        ]
                    }
                ]
            }
        }
    )
    # Mock stocks
    respx.get(
        url__startswith="https://query1.finance.yahoo.com/v7/finance/spark"
    ).respond(
        json={
            "spark": {
                "result": [
                    {
                        "symbol": "PETR4.SA",
                        "response": [
                            {
                                "timestamp": list(range(30)),
                                "indicators": {"quote": [{"close": [10.0] * 30}]},
                            }
                        ],
                    }
                ]
            }
        }
    )

    success = collect_and_save()
    assert success is True

    data = get_latest_dolar_correlation_data()
    assert data is not None
    assert json.loads(data.positivas_json) == []  # since returns are 0, pearson is 0
    assert json.loads(data.negativas_json) == []


@respx.mock
def test_collect_and_save_failure(isolated_db, monkeypatch):
    respx.get(
        url__startswith="https://query1.finance.yahoo.com/v7/finance/spark"
    ).respond(status_code=500)

    # patch sleep to speed up
    monkeypatch.setattr("app.collectors.utils.time.sleep", lambda s: None)

    success = collect_and_save()
    assert success is False
