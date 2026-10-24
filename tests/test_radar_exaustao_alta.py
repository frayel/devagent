import json
from datetime import datetime, timezone
from unittest.mock import patch

from app.collectors import radar_exaustao_alta
from app.database import ExaustaoAltaData


@patch("app.collectors.radar_exaustao_alta.fetch_historico_diario_yfinance_spark")
def test_coleta_sucesso(mock_fetch):
    mock_fetch.return_value = [
        {
            "symbol": "PETR4.SA",
            "response": [
                {
                    "indicators": {
                        "quote": [
                            {
                                "close": [10.0, 10.3],
                                "open": [10.0, 10.0],
                                "high": [
                                    10.0,
                                    11.0,
                                ],  # corpo=0.3, sombra_sup = 11 - 10.3 = 0.7. 0.7 > 2*0.3
                            }
                        ]
                    }
                }
            ],
        },
        {
            "symbol": "VALE3.SA",
            "response": [
                {
                    "indicators": {
                        "quote": [
                            {
                                "close": [20.0, 20.4],
                                "open": [20.0, 20.0],
                                "high": [
                                    20.0,
                                    20.5,
                                ],  # corpo=0.4, sombra_sup = 20.5 - 20.4 = 0.1.
                            }
                        ]
                    }
                }
            ],
        },
    ]

    data = radar_exaustao_alta.fetch_yfinance()
    assert data is not None
    alertas = json.loads(data.alertas_json)
    assert len(alertas) == 1
    assert alertas[0]["ticker"] == "PETR4"


@patch("app.collectors.radar_exaustao_alta.fetch_yfinance")
@patch("app.collectors.radar_exaustao_alta.save_exaustao_alta_data")
def test_collect_and_save(mock_save, mock_fetch):
    mock_fetch.return_value = ExaustaoAltaData(
        timestamp=datetime.now(timezone.utc), alertas_json="[]", fonte="yfinance"
    )
    result = radar_exaustao_alta.collect_and_save()
    assert result is True
    mock_save.assert_called_once()
