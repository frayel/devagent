import json
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.database import (
    IbovespaData,
    HighlightsData,
    save_ibovespa_data,
    save_highlights_data,
)
from app.main import app

client = TestClient(app)


def test_snapshot_with_data():
    now = datetime.now(timezone.utc)
    history = {"dates": ["2026-09-25", "2026-09-28"], "closes": [182050.1, 183476.86]}

    data = IbovespaData(
        timestamp=now,
        current_price=183476.86,
        previous_close=182050.10,
        history_json=json.dumps(history),
        fonte="brapi",
    )
    save_ibovespa_data(data)

    highlights_data = HighlightsData(
        timestamp=now,
        highs_json=json.dumps(
            [{"ticker": "HIGH1", "price": 10.0, "change_percent": 5.0}]
        ),
        lows_json=json.dumps(
            [{"ticker": "LOW1", "price": 5.0, "change_percent": -5.0}]
        ),
        fonte="yfinance",
    )
    save_highlights_data(highlights_data)

    response = client.get("/api/snapshot")
    assert response.status_code == 200

    resp_data = response.json()
    assert "gerado_em" in resp_data
    assert "paineis" in resp_data

    ibov = resp_data["paineis"]["ibovespa"]
    assert ibov["valor"] == 183476.86
    assert ibov["fechamento_anterior"] == 182050.10
    import pytest

    # calculation: (183476.86 - 182050.10) / 182050.10 * 100
    expected_pct = ((183476.86 - 182050.10) / 182050.10) * 100
    assert ibov["variacao_pct"] == pytest.approx(expected_pct)
    assert ibov["coletado_em"] == now.isoformat()
    assert ibov["fonte"] == "brapi"
    assert ibov["historico"]["datas"] == ["2026-09-25", "2026-09-28"]
    assert ibov["historico"]["fechamentos"] == [182050.1, 183476.86]

    altas_baixas = resp_data["paineis"]["altas_baixas"]
    assert altas_baixas["fonte"] == "yfinance"
    assert altas_baixas["altas"] == [
        {"ticker": "HIGH1", "price": 10.0, "change_percent": 5.0}
    ]
    assert altas_baixas["baixas"] == [
        {"ticker": "LOW1", "price": 5.0, "change_percent": -5.0}
    ]
