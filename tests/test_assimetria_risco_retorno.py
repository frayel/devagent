from datetime import datetime, timezone
import json
from app.database import (
    AssimetriaRiscoRetornoData,
    save_assimetria_risco_retorno_data,
    get_latest_assimetria_risco_retorno_data,
    init_db,
)
from app.collectors import assimetria_risco_retorno


def test_db_save_and_get():
    init_db()
    agora = datetime.now(timezone.utc)
    alertas = [{"ticker": "PETR4", "dist_min_pct": 1.0, "dist_max_pct": 12.0}]
    data = AssimetriaRiscoRetornoData(
        timestamp=agora, alertas_json=json.dumps(alertas), fonte="mock"
    )
    save_assimetria_risco_retorno_data(data)

    retrieved = get_latest_assimetria_risco_retorno_data()
    assert retrieved is not None
    assert retrieved.fonte == "mock"

    parsed = json.loads(retrieved.alertas_json)
    assert len(parsed) == 1
    assert parsed[0]["ticker"] == "PETR4"


def test_assimetria_logic(monkeypatch):
    init_db()

    def mock_fetch(*args, **kwargs):
        return [
            {
                "symbol": "PETR4",
                "timestamp": list(range(40)),
                "indicators": {
                    "quote": [
                        {
                            "close": [10.0] * 29
                            + [
                                8.0,
                                10.0,
                                11.0,
                                12.0,
                                13.0,
                                10.0,
                                9.0,
                                8.5,
                                8.1,
                                8.05,
                                8.0,
                            ]
                        }
                    ]
                },
            },
            {
                "symbol": "VALE3",
                "timestamp": list(range(40)),
                "indicators": {"quote": [{"close": [50.0] * 30 + [50.0, 50.0, 50.0]}]},
            },
        ]

    monkeypatch.setattr(
        "app.collectors.assimetria_risco_retorno.fetch_historico_diario_yfinance_spark",
        mock_fetch,
    )

    success = assimetria_risco_retorno.collect_and_save()
    assert success

    data = get_latest_assimetria_risco_retorno_data()
    assert data is not None

    alertas = json.loads(data.alertas_json)
    assert len(alertas) == 1
    assert alertas[0]["ticker"] == "PETR4"
    assert alertas[0]["dist_min_pct"] == 0.0
    assert alertas[0]["dist_max_pct"] == 62.5
