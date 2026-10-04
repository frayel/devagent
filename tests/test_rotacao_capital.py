import pytest
import respx
from httpx import Response
from app.database import get_latest_rotacao_capital_data, init_db, get_connection
from app.collectors.rotacao_capital import collect_and_save


@pytest.fixture(autouse=True)
def clean_db():
    init_db()
    conn = get_connection()
    conn.execute("DELETE FROM rotacao_capital_cache")
    conn.commit()
    conn.close()


def mock_yfinance_spark(respx_mock, bancos_ret, comm_ret):
    def make_result(symbol, ret):
        prev = 100.0
        current = prev * (1 + ret / 100.0)
        return {
            "symbol": symbol,
            "response": [
                {
                    "meta": {"chartPreviousClose": prev},
                    "indicators": {"quote": [{"close": [current]}]},
                }
            ],
        }

    results = []
    for s in ["ITUB4.SA", "BBDC4.SA", "BBAS3.SA"]:
        results.append(make_result(s, bancos_ret))
    for s in ["VALE3.SA", "PETR4.SA", "PRIO3.SA"]:
        results.append(make_result(s, comm_ret))

    url = "https://query1.finance.yahoo.com/v7/finance/spark?symbols=ITUB4.SA,BBDC4.SA,BBAS3.SA,VALE3.SA,PETR4.SA,PRIO3.SA&range=1d&interval=1d"
    respx_mock.get(url).mock(
        return_value=Response(200, json={"spark": {"result": results}})
    )


@respx.mock
def test_rotacao_bancos(respx_mock):
    mock_yfinance_spark(respx_mock, 1.0, -1.0)
    assert collect_and_save()
    data = get_latest_rotacao_capital_data()
    assert data is not None
    assert data.estado == "Para Bancos"
    assert pytest.approx(data.var_bancos) == 1.0
    assert pytest.approx(data.var_commodities) == -1.0


@respx.mock
def test_rotacao_commodities(respx_mock):
    mock_yfinance_spark(respx_mock, -2.0, 1.5)
    assert collect_and_save()
    data = get_latest_rotacao_capital_data()
    assert data.estado == "Para Commodities"


@respx.mock
def test_rotacao_neutra(respx_mock):
    mock_yfinance_spark(respx_mock, 0.2, -0.2)
    assert collect_and_save()
    data = get_latest_rotacao_capital_data()
    assert data.estado == "Neutra"


@respx.mock
def test_api_falha(respx_mock):
    respx_mock.get(
        "https://query1.finance.yahoo.com/v7/finance/spark?symbols=ITUB4.SA,BBDC4.SA,BBAS3.SA,VALE3.SA,PETR4.SA,PRIO3.SA&range=1d&interval=1d"
    ).mock(return_value=Response(500))
    assert not collect_and_save()
    assert get_latest_rotacao_capital_data() is None
