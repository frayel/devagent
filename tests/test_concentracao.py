import respx
import json
from app.collectors.concentracao import fetch_yfinance


@respx.mock
def test_concentracao_success():
    respx.get(
        url__startswith="https://query1.finance.yahoo.com/v7/finance/spark"
    ).respond(
        status_code=200,
        json={
            "spark": {
                "result": [
                    {
                        "symbol": "^BVSP",
                        "response": [
                            {"indicators": {"quote": [{"close": [100000, 101000]}]}}
                        ],
                    },
                    {
                        "symbol": "VALE3.SA",
                        "response": [
                            {"indicators": {"quote": [{"close": [100.0, 105.0]}]}}
                        ],
                    },
                ]
            }
        },
    )
    data = fetch_yfinance()
    assert data is not None
    resumo = json.loads(data.resumo_json)
    assert "Dos 1000 pontos" in resumo["mensagem"]


@respx.mock
def test_concentracao_invariant():
    respx.get(
        url__startswith="https://query1.finance.yahoo.com/v7/finance/spark"
    ).respond(
        status_code=200,
        json={
            "spark": {
                "result": [
                    {
                        "symbol": "^BVSP",
                        "response": [
                            {"indicators": {"quote": [{"close": [100000, 101000]}]}}
                        ],
                    },
                    {
                        "symbol": "VALE3.SA",
                        "response": [
                            {"indicators": {"quote": [{"close": [100.0, 105.0]}]}}
                        ],
                    },
                ]
            }
        },
    )
    data = fetch_yfinance()
    assert data is not None
    top3 = json.loads(data.top3_json)
    soma_pontos = sum(abs(a["pontos"]) for a in top3)
    # The sum of points shouldn't exceed ibov variation. The actual test code above was doing 5% of VALE * 12% * 100000 = 600 points.
    assert soma_pontos <= 1000


@respx.mock
def test_concentracao_failure():
    respx.get(
        url__startswith="https://query1.finance.yahoo.com/v7/finance/spark"
    ).respond(status_code=500)
    data = fetch_yfinance()
    assert data is None


@respx.mock
def test_concentracao_stable():
    respx.get(
        url__startswith="https://query1.finance.yahoo.com/v7/finance/spark"
    ).respond(
        status_code=200,
        json={
            "spark": {
                "result": [
                    {
                        "symbol": "^BVSP",
                        "response": [
                            {"indicators": {"quote": [{"close": [100000, 100050]}]}}
                        ],
                    },
                ]
            }
        },
    )
    data = fetch_yfinance()
    assert data is not None
    resumo = json.loads(data.resumo_json)
    assert resumo["estado"] == "estavel"
