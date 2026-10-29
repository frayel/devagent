from datetime import datetime, timezone
import json
from fastapi.testclient import TestClient


def test_heatmap_mare(setup_db):
    from app.main import app
    from app.database import MareData, save_mare_data

    heatmap_data = [
        {"ticker": "PETR4", "variacao": 2.5, "financeiro": 1500000, "peso": 0.5},
        {"ticker": "VALE3", "variacao": -1.2, "financeiro": 1000000, "peso": 0.33},
        {"ticker": "ITUB4", "variacao": 0.0, "financeiro": 500000, "peso": 0.17},
    ]

    agora = datetime.now(timezone.utc)
    dado = MareData(
        timestamp=agora,
        valor=68,
        fluxo=74.0,
        calma=61.0,
        volume=62.0,
        ativos_json=json.dumps(heatmap_data),
        historico_json="[]",
        fonte="demonstracao",
    )
    save_mare_data(dado)

    client = TestClient(app)
    html = client.get("/").text

    assert 'class="heatmap"' in html
    assert "PETR4" in html
    assert "VALE3" in html
    assert "ITUB4" in html

    assert "var(--cor-alta)" in html
    assert "var(--cor-baixa)" in html
    assert "var(--cor-neutro)" in html
