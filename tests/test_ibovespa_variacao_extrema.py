"""Variação diária real acima de 12% não é descartada (29/10/2026).

Nesse dia o Ibovespa variou 15,99%, com os limites do circuit breaker da B3
estendidos, e o coletor descartou o dado: "yfinance returned implausible
variation: 15.99%". O limite passou a 20%.
"""

import pytest
import respx

from app.collectors import ibovespa

URL = "https://query2.finance.yahoo.com/v8/finance/chart/^BVSP?range=1y&interval=1d"


def _chart(fechamento_anterior: float, atual: float) -> dict:
    return {
        "chart": {
            "result": [
                {
                    "meta": {
                        "regularMarketPrice": atual,
                        "chartPreviousClose": fechamento_anterior,
                    },
                    "timestamp": [1761652800, 1761739200],
                    "indicators": {"quote": [{"close": [fechamento_anterior, atual]}]},
                }
            ]
        }
    }


@pytest.fixture(autouse=True)
def sem_espera(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.collectors.utils.time.sleep", lambda s: None)


@respx.mock
def test_variacao_de_16_por_cento_e_aceita():
    respx.get(URL).respond(200, json=_chart(100_000.0, 115_990.0))

    dado = ibovespa.fetch_yfinance()

    assert dado is not None
    assert dado.current_price == 115_990.0
    assert dado.previous_close == 100_000.0


@respx.mock
def test_variacao_acima_de_20_por_cento_continua_descartada():
    respx.get(URL).respond(200, json=_chart(100_000.0, 125_000.0))

    assert ibovespa.fetch_yfinance() is None


def test_limite_e_20_por_cento():
    assert ibovespa.VARIACAO_DIARIA_MAXIMA == 20.0
