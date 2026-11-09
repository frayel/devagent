"""Variação diária real acima de 12% não é descartada (29/10/2026).

Nesse dia foi relatado que o Ibovespa teria variado 15,99% (relatado, não confirmado por fonte independente),
com os limites do circuit breaker da B3 estendidos, e o coletor descartou o dado. O limite passou a 20%.
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
def test_variacao_de_16_por_cento_e_aceita(monkeypatch):
    respx.get(URL).respond(200, json=_chart(100_000.0, 115_990.0))

    dado = ibovespa.fetch_yfinance()

    assert dado is not None
    assert dado.current_price == 115_990.0
    assert dado.previous_close == 100_000.0

    # Com segunda fonte confirmando, collect_and_save aceita e grava
    monkeypatch.setattr(
        "app.collectors.ibovespa.obter_variacao_segunda_fonte",
        lambda fonte: 15.99,
    )
    salvou = []
    monkeypatch.setattr(
        "app.collectors.ibovespa.save_ibovespa_data",
        lambda d: salvou.append(d),
    )
    assert ibovespa.collect_and_save() is True
    assert len(salvou) == 1


@respx.mock
def test_variacao_acima_de_20_por_cento_continua_descartada(monkeypatch):
    respx.get(URL).respond(200, json=_chart(100_000.0, 125_000.0))

    assert ibovespa.fetch_yfinance() is None

    # Mesmo com segunda fonte concordando, 25% é descartada
    monkeypatch.setattr(
        "app.collectors.ibovespa.obter_variacao_segunda_fonte",
        lambda fonte: 25.0,
    )
    assert ibovespa.collect_and_save() is False


def test_limite_e_20_por_cento():
    assert ibovespa.VARIACAO_DIARIA_MAXIMA == 20.0
