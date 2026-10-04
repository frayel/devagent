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
