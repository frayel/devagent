import respx
import httpx
from datetime import datetime, timezone
from app.collectors.rotacao_capital import fetch_yfinance, collect_and_save
from app.database import get_latest_rotacao_capital_data


@respx.mock
def test_fetch_yfinance_success():
    bancos = ["ITUB4.SA", "BBDC4.SA", "BBAS3.SA"]
    commodities = ["VALE3.SA", "PETR4.SA", "PRIO3.SA"]
    symbols = ",".join(bancos + commodities)
    url = f"https://query1.finance.yahoo.com/v7/finance/spark?symbols={symbols}&range=1d&interval=1d"

    mock_response = {
        "spark": {
            "result": [
                {
                    "symbol": "ITUB4.SA",
                    "response": [
                        {
                            "meta": {"chartPreviousClose": 100.0},
                            "indicators": {"quote": [{"close": [101.0]}]},
                        }
                    ],
                },
                {
                    "symbol": "VALE3.SA",
                    "response": [
                        {
                            "meta": {"chartPreviousClose": 100.0},
                            "indicators": {"quote": [{"close": [99.0]}]},
                        }
                    ],
                },
            ]
        }
    }
    respx.get(url).mock(return_value=httpx.Response(200, json=mock_response))

    data = fetch_yfinance()
    assert data is not None
    assert data.estado == "Para Bancos"
    assert data.fonte == "yfinance"


def test_collect_and_save_success(monkeypatch, setup_db):
    def mock_fetch():
        from app.database import RotacaoCapitalData

        return RotacaoCapitalData(
            timestamp=datetime.now(timezone.utc),
            estado="Para Bancos",
            var_bancos=1.0,
            var_commodities=-1.0,
            fonte="yfinance",
        )

    monkeypatch.setattr("app.collectors.rotacao_capital.fetch_yfinance", mock_fetch)

    assert collect_and_save() is True

    data = get_latest_rotacao_capital_data()
    assert data is not None
    assert data.estado == "Para Bancos"
    assert data.var_bancos == 1.0
