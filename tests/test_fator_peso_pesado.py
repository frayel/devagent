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
    # As 5 maiores contribuem 800 pts, só pela VALE3 (peso 12%):
    # var% / 100 × 12 / 100 × 130000 = 800 => var% = 5,128205% (spec 143).
    mock_yfinance("VALE3.SA", 105.128205, 100.0)
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


@pytest.mark.parametrize(
    ("proporcao", "modulo"),
    [(-50.8, "50,8%"), (50.8, "50,8%"), (150.0, "150,0%"), (-150.0, "150,0%")],
)
def test_frase_traz_o_modulo_sem_sinal(proporcao, modulo):
    """Issue #835: o sentido está nas palavras; o número da frase não tem sinal."""
    from app.services.fator_peso_pesado import frase

    texto = frase(proporcao, False)
    assert f"somando {modulo} do tamanho" in texto
    assert "+" not in texto
    assert "−" not in texto
