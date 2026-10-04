import json
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.database import (
    IbovespaData,
    HighlightsData,
    ConcentracaoData,
    save_ibovespa_data,
    save_highlights_data,
    save_concentracao_data,
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
        up_count=1,
        down_count=1,
        total_count=2,
    )
    save_highlights_data(highlights_data)

    concentracao_data = ConcentracaoData(
        timestamp=now,
        resumo_json=json.dumps(
            {"estado": "concentrado", "mensagem": "Dos 1000 pontos..."}
        ),
        top3_json=json.dumps([{"ticker": "VALE3", "pontos": 500, "peso": 0.12}]),
        fonte="yfinance",
    )
    save_concentracao_data(concentracao_data)

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
    assert "dispersao" in altas_baixas
    assert altas_baixas["dispersao"]["em_alta"] == 1
    assert altas_baixas["dispersao"]["em_baixa"] == 1
    assert altas_baixas["dispersao"]["proporcao_alta_pct"] == 50.0

    assert "concentracao" in resp_data["paineis"]
    assert resp_data["paineis"]["concentracao"]["fonte"] == "yfinance"
    assert resp_data["paineis"]["concentracao"]["resumo"]["estado"] == "concentrado"
    assert len(resp_data["paineis"]["concentracao"]["top3"]) == 1
    assert resp_data["paineis"]["concentracao"]["top3"][0]["ticker"] == "VALE3"
