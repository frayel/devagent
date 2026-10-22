import pytest
from app.collectors import fator_peso_pesado
from app.database import init_db


@pytest.fixture
def mock_yfinance(respx_mock):
    def _mock_chart(ticker, current, previous):
        respx_mock.get(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=1d&interval=1d"
        ).respond(
            json={
                "chart": {
                    "result": [
                        {
                            "meta": {
                                "regularMarketPrice": current,
                                "chartPreviousClose": previous,
                            }
                        }
                    ]
                }
            }
        )
        respx_mock.get(
            f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}?range=1d&interval=1d"
        ).respond(
            json={
                "chart": {
                    "result": [
                        {
                            "meta": {
                                "regularMarketPrice": current,
                                "chartPreviousClose": previous,
                            }
                        }
                    ]
                }
            }
        )

    return _mock_chart


def test_fator_peso_pesado_sucesso(mock_yfinance, setup_db):
    init_db()
    mock_yfinance("^BVSP", 131000, 130000)  # IBOV sobe 1000 pontos
    # We want top 5 to contribute 800 pts.
    # Total formula: sum(var_pct * weight / 100) * ibov_prev = 800
    # sum(var_pct * weight / 100) = 800 / 130000 = 0.0061538
    # Let's just make VALE3 vary and the others 0.
    # VALE3 weight = 12.0
    # var_pct * 12.0 / 100 = 800 / 130000
    # var_pct = (800 / 130000) * 100 / 12 = 0.051282
    # var_pct = (curr - prev)/prev * 100 => 0.051282 * prev = (curr-prev)*100
    # Let prev = 100 => curr = 100 + (0.051282) = 100.051282

    # Actually, simpler:
    # PTS contrib VALE = 800 => (var_pct * 12 / 100) * 130000 = 800
    # var_pct = 800 / (12 * 1300) = 800 / 15600 = 5.128205 %
    # prev = 100, curr = 105.128205

    mock_yfinance("VALE3.SA", 100.05128205, 100.0)
    mock_yfinance("PETR4.SA", 100.0, 100.0)
    mock_yfinance("ITUB4.SA", 100.0, 100.0)
    mock_yfinance("PETR3.SA", 100.0, 100.0)
    mock_yfinance("BBAS3.SA", 100.0, 100.0)

    result = fator_peso_pesado.collect_and_save()
    assert result is True

    from app.database import get_latest_fator_peso_pesado_data

    data = get_latest_fator_peso_pesado_data()
    assert data is not None
    assert data.mercado_lateral is False
    assert abs(data.proporcao - 80.0) < 0.1  # Should be close to 80%


def test_fator_peso_pesado_mercado_lateral(mock_yfinance, setup_db):
    init_db()
    mock_yfinance(
        "^BVSP", 130050, 130000
    )  # IBOV sobe 50 pontos, 50 / 130000 = 0.038% (< 0.1%)

    result = fator_peso_pesado.collect_and_save()
    assert result is True

    from app.database import get_latest_fator_peso_pesado_data

    data = get_latest_fator_peso_pesado_data()
    assert data is not None
    assert data.mercado_lateral is True
    assert data.proporcao == 0.0
