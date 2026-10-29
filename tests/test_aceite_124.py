from datetime import datetime, date, timezone
from app.banco import gravar_snapshot, ler_snapshot, lendo_pregao, init_db
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_lendo_pregao_context_manager():
    init_db()
    d1 = date(2023, 10, 26)
    d2 = date(2023, 10, 27)

    payload_d1 = {
        "valor": 111111,
        "timestamp": datetime(2023, 10, 26, tzinfo=timezone.utc).isoformat(),
        "current_price": 111111.0,
        "previous_close": 110000.0,
        "history_json": "{}",
        "fonte": "test",
    }
    payload_d2 = {
        "valor": 222222,
        "timestamp": datetime(2023, 10, 27, tzinfo=timezone.utc).isoformat(),
        "current_price": 222222.0,
        "previous_close": 111111.0,
        "history_json": "{}",
        "fonte": "test",
    }

    gravar_snapshot("ibovespa", d1, "final", "test", payload_d1)
    gravar_snapshot("ibovespa", d2, "final", "test", payload_d2)

    res = ler_snapshot("ibovespa")
    assert res["valor"] == 222222

    with lendo_pregao(d1):
        res_d1 = ler_snapshot("ibovespa")
        assert res_d1["valor"] == 111111

    res_after = ler_snapshot("ibovespa")
    assert res_after["valor"] == 222222

    try:
        with lendo_pregao(d1):
            raise ValueError("Test error")
    except ValueError:
        pass

    res_after_exception = ler_snapshot("ibovespa")
    assert res_after_exception["valor"] == 222222


def test_api_snapshot_and_index():
    init_db()
    d1_str = "2023-10-26"
    d1 = date(2023, 10, 26)
    d2 = date(2023, 10, 27)

    payload_d1 = {
        "valor": 111111,
        "timestamp": datetime(2023, 10, 26, 18, 0, tzinfo=timezone.utc).isoformat(),
        "current_price": 111111.0,
        "previous_close": 110000.0,
        "history_json": "{}",
        "fonte": "test",
    }
    payload_d2 = {
        "valor": 222222,
        "timestamp": datetime(2023, 10, 27, 18, 0, tzinfo=timezone.utc).isoformat(),
        "current_price": 222222.0,
        "previous_close": 111111.0,
        "history_json": "{}",
        "fonte": "test",
    }

    gravar_snapshot("ibovespa", d1, "final", "test", payload_d1)
    gravar_snapshot("ibovespa", d2, "final", "test", payload_d2)

    payload_only_d2 = {"alertas_json": "[]"}
    gravar_snapshot("radar_anomalia_fechamento", d2, "final", "test", payload_only_d2)

    res = client.get("/api/snapshot")
    assert res.json()["paineis"]["ibovespa"]["valor"] == 222222.0

    res_d1 = client.get(f"/api/snapshot?data={d1_str}")
    data = res_d1.json()
    assert data["paineis"]["ibovespa"]["valor"] == 111111.0
    assert data["paineis"]["anomalia_fechamento"] is None

    res_html = client.get("/")
    assert "222.222" in res_html.text or "222222" in res_html.text.replace(".", "")
    assert "Sem registro neste pregão" not in res_html.text

    res_html_d1 = client.get(f"/?data={d1_str}")
    assert "111.111" in res_html_d1.text or "111111" in res_html_d1.text.replace(
        ".", ""
    )
    assert "Sem registro neste pregão" in res_html_d1.text

    from app.database import get_latest_ibovespa_data

    latest = get_latest_ibovespa_data()
    assert latest.current_price == 222222.0
