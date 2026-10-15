import re
import respx
import json
from app.collectors.concentracao import (
    fetch_yfinance,
    fetch_concentracao_vendedora_yfinance,
)


@respx.mock
def test_concentracao_success():
    respx.get(
        url__regex=r"https://query[12]\.finance\.yahoo\.com/v7/finance/spark.*"
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
        url__regex=r"https://query[12]\.finance\.yahoo\.com/v7/finance/spark.*"
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
        url__regex=r"https://query[12]\.finance\.yahoo\.com/v7/finance/spark.*"
    ).respond(status_code=500)
    data = fetch_yfinance()
    assert data is None


@respx.mock
def test_concentracao_stable():
    respx.get(
        url__regex=r"https://query[12]\.finance\.yahoo\.com/v7/finance/spark.*"
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


@respx.mock
def test_fetch_concentracao_vendedora_queda():
    mock_url_1 = re.compile(r"https://query1\.finance\.yahoo\.com/v7/finance/spark.*")
    mock_url_2 = re.compile(r"https://query2\.finance\.yahoo\.com/v7/finance/spark.*")

    # Mock data where BVSP goes down by 1000 points (from 101000 to 100000)
    # PETR4 down 10% (100 -> 90), weight 0.08. Impact = -0.10 * 0.08 * 101000 = -808 pts
    # VALE3 down 5% (100 -> 95), weight 0.12. Impact = -0.05 * 0.12 * 101000 = -606 pts
    # Total negative contribution to check logic
    mock_response = {
        "spark": {
            "result": [
                {
                    "symbol": "^BVSP",
                    "response": [
                        {"indicators": {"quote": [{"close": [101000, 100000]}]}}
                    ],
                },
                {
                    "symbol": "PETR4.SA",
                    "response": [{"indicators": {"quote": [{"close": [100, 90]}]}}],
                },
                {
                    "symbol": "VALE3.SA",
                    "response": [{"indicators": {"quote": [{"close": [100, 95]}]}}],
                },
            ]
        }
    }

    respx.get(mock_url_1).respond(json=mock_response)
    respx.get(mock_url_2).respond(json=mock_response)

    data = fetch_concentracao_vendedora_yfinance()
    assert data is not None
    import json

    resumo = json.loads(data.resumo_json)
    assert resumo["estado"] == "vendedora"
    assert "piores ativos hoje respondem por" in resumo["mensagem"]


@respx.mock
def test_fetch_concentracao_vendedora_alta():
    mock_url_1 = re.compile(r"https://query1\.finance\.yahoo\.com/v7/finance/spark.*")
    mock_url_2 = re.compile(r"https://query2\.finance\.yahoo\.com/v7/finance/spark.*")

    # Mock data where BVSP goes UP
    mock_response = {
        "spark": {
            "result": [
                {
                    "symbol": "^BVSP",
                    "response": [
                        {"indicators": {"quote": [{"close": [100000, 101000]}]}}
                    ],
                }
            ]
        }
    }

    respx.get(mock_url_1).respond(json=mock_response)
    respx.get(mock_url_2).respond(json=mock_response)

    data = fetch_concentracao_vendedora_yfinance()
    # Should return None when Ibovespa is positive
    assert data is None
