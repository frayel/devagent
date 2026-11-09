import re
import json

import respx
from fastapi.testclient import TestClient

from app.collectors.highlights import (
    TICKERS,
    collect_and_save,
    fetch_yfinance,
)
from app.database import get_latest_highlights_data
from app.main import app

client = TestClient(app)


SPARK = r"https://query[12]\.finance\.yahoo\.com/v8/finance/spark.*"


def spark_com_precos(precos: dict[str, float]) -> dict:
    """Spark do Yahoo com fechamento anterior 90 para todos os símbolos."""
    return {
        "spark": {
            "result": [
                {
                    "symbol": f"{ticker}.SA",
                    "response": [
                        {
                            "meta": {
                                "regularMarketPrice": preco,
                                "previousClose": 90.0,
                                "chartPreviousClose": 90.0,
                            }
                        }
                    ],
                }
                for ticker, preco in precos.items()
            ]
        }
    }


def generate_mock_yfinance_data(ticker, is_high=False, multiplier=1):
    price = (92.0 + multiplier * 0.5) if is_high else (88.0 - multiplier * 0.5)
    return {
        "spark": {
            "result": [
                {
                    "symbol": f"{ticker}.SA",
                    "response": [
                        {
                            "meta": {
                                "regularMarketPrice": price,
                                "previousClose": 90.0,
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
        price = (92.0 + multiplier * 0.5) if is_high else (88.0 - multiplier * 0.5)
        results.append(
            {
                "symbol": f"{ticker}.SA",
                "response": [
                    {
                        "meta": {
                            "regularMarketPrice": price,
                            "previousClose": 90.0,
                            "chartPreviousClose": 90.0,
                        }
                    }
                ],
            }
        )
    return {"spark": {"result": results}}


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
def test_collect_and_save_pelo_yahoo(monkeypatch):
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

    assert collect_and_save() is True
    assert get_latest_highlights_data() is not None


@respx.mock
def test_index_route(monkeypatch):
    precos = {f"HIGH{i}": 92.0 + i * 1.0 for i in range(5)}
    precos.update({f"LOW{i}": 88.0 - i * 1.0 for i in range(5)})
    monkeypatch.setattr("app.collectors.highlights.TICKERS", list(precos))
    monkeypatch.setattr("app.collectors.utils.time.sleep", lambda s: None)
    respx.get(url__regex=SPARK).respond(200, json=spark_com_precos(precos))
    collect_and_save()

    response = client.get("/")
    assert response.status_code == 200
    assert "Maiores altas" in response.text
    assert "Maiores baixas" in response.text
    assert "HIGH0" in response.text
    assert "LOW0" in response.text
    assert "Fonte yfinance" in response.text
    assert "Dispersão" in response.text
    assert "5 subiram</span>" in response.text


@respx.mock
def test_fetch_less_than_5_assets(monkeypatch):
    precos = {f"ASSET{i}": 92.0 + i * 1.0 for i in range(3)}
    monkeypatch.setattr("app.collectors.highlights.TICKERS", list(precos))
    monkeypatch.setattr("app.collectors.utils.time.sleep", lambda s: None)
    respx.get(url__regex=SPARK).respond(200, json=spark_com_precos(precos))
    collect_and_save()

    response = client.get("/")
    assert response.status_code == 200
    assert "ASSET0" in response.text
    assert "Dispersão" in response.text
    assert "3 subiram</span>" in response.text


@respx.mock
def test_index_route_yfinance(monkeypatch):
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
    collect_and_save()

    response = client.get("/")
    assert response.status_code == 200
    assert "Fonte yfinance" in response.text
    assert "Dispersão" in response.text
    assert "15 subiram</span>" in response.text
