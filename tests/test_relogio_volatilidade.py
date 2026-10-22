import json

import respx
from httpx import Response
from app.collectors.relogio_volatilidade import collect_and_save


def test_relogio_volatilidade_sucesso(setup_db):
    # Mocking successful yahoo finance response
    yahoo_url = (
        "https://query1.finance.yahoo.com/v8/finance/chart/^BVSP?range=1d&interval=15m"
    )

    mock_data = {
        "chart": {
            "result": [
                {
                    "meta": {
                        "regularMarketPrice": 120000,
                        "previousClose": 119000,
                        "regularMarketDayLow": 118000,
                        "regularMarketDayHigh": 121000,
                    },
                    "timestamp": [1609423200, 1609424100, 1609425000],
                    "indicators": {
                        "quote": [
                            {
                                "high": [120500, 121000, 119500],
                                "low": [119500, 118000, 119000],
                            }
                        ]
                    },
                }
            ]
        }
    }

    with respx.mock:
        respx.get(yahoo_url).mock(return_value=Response(200, json=mock_data))
        respx.get(yahoo_url.replace("query1", "query2")).mock(
            return_value=Response(200, json=mock_data)
        )

        result = collect_and_save()
        assert result is True

        from app.database import get_latest_relogio_volatilidade_data

        data = get_latest_relogio_volatilidade_data()

        assert data is not None
        alertas = json.loads(data.alertas_json)
        assert alertas["ticker"] == "^BVSP"
        assert alertas["variacao"] == 1000
        assert (
            alertas["pico_horario"] == 1609424100
        )  # second timestamp has highest amplitude (3000)
        assert alertas["amplitude_percentual"] == (3000 / 119000) * 100


def test_relogio_volatilidade_falha_api(setup_db):
    yahoo_url = (
        "https://query1.finance.yahoo.com/v8/finance/chart/^BVSP?range=1d&interval=15m"
    )
    with respx.mock:
        respx.get(yahoo_url).mock(return_value=Response(500))
        assert collect_and_save() is False
