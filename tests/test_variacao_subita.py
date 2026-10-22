import re
import json
from datetime import datetime, timezone
import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from app.database import get_connection, save_variacao_subita_data, VariacaoSubitaData
import app.banco
from app.collectors import variacao_subita
from app.main import app


@pytest.fixture(autouse=True)
def _limpar_banco():
    import app.banco as app_banco

    app_banco._db_initialized = False
    app_banco.init_db()
    conn = get_connection()
    conn.execute("DELETE FROM snapshots_paineis WHERE painel = 'variacao_subita'")
    conn.commit()
    conn.close()


def mock_yfinance_response(with_alerts=True):
    response = {
        "spark": {
            "result": [
                {
                    "symbol": "PETR4.SA",
                    "response": [
                        {
                            "indicators": {
                                "quote": [
                                    {
                                        "close": [10.0, 10.1, 10.2, 10.3, 10.1]
                                        if not with_alerts
                                        else [10.0, 10.1, 10.2, 10.3, 10.5]
                                    }
                                ]
                            }
                        }
                    ],
                }
            ]
        }
    }
    return httpx.Response(200, json=response)


@respx.mock
def test_coletor_com_alertas():
    respx.get(
        re.compile(
            r"https://query[12]\.finance\.yahoo\.com/v7/finance/spark\?symbols=PETR4\.SA,VALE3\.SA,ITUB4\.SA,BBDC4\.SA,B3SA3\.SA,ABEV3\.SA,ELET3\.SA,RENT3\.SA,WEGE3\.SA,BBAS3\.SA,ITSA4\.SA,SUZB3\.SA,BPAC11\.SA,RADL3\.SA,EQTL3\.SA&range=1d&interval=15m"
        )
    ).mock(return_value=mock_yfinance_response(with_alerts=True))
    respx.get(
        re.compile(
            r"https://query[12]\.finance\.yahoo\.com/v7/finance/spark\?symbols=CSAN3\.SA,PRIO3\.SA,RDOR3\.SA,RAIL3\.SA,SBSP3\.SA,VIVT3\.SA,CMIG4\.SA,LREN3\.SA,CPLE6\.SA,UGPA3\.SA,ENEV3\.SA,TIMS3\.SA,TOTS3\.SA,EGIE3\.SA,HAPV3\.SA&range=1d&interval=15m"
        )
    ).mock(return_value=httpx.Response(200, json={"spark": {"result": []}}))

    assert variacao_subita.collect_and_save() is True

    import app.banco as app_banco

    app_banco._db_initialized = False
    app_banco.init_db()
    conn = get_connection()
    row = conn.execute(
        "SELECT payload FROM snapshots_paineis WHERE painel = 'variacao_subita' ORDER BY data_referencia DESC LIMIT 1"
    ).fetchone()
    conn.close()

    assert row is not None
    payload = json.loads(row["payload"])
    alertas = json.loads(payload["alertas_json"])
    assert len(alertas) == 1
    assert alertas[0]["ticker"] == "PETR4"
    assert alertas[0]["change_percent"] == 5.0  # (10.5 - 10.0) / 10.0


@respx.mock
def test_coletor_sem_alertas():
    respx.get(
        re.compile(
            r"https://query[12]\.finance\.yahoo\.com/v7/finance/spark\?symbols=PETR4\.SA,VALE3\.SA,ITUB4\.SA,BBDC4\.SA,B3SA3\.SA,ABEV3\.SA,ELET3\.SA,RENT3\.SA,WEGE3\.SA,BBAS3\.SA,ITSA4\.SA,SUZB3\.SA,BPAC11\.SA,RADL3\.SA,EQTL3\.SA&range=1d&interval=15m"
        )
    ).mock(return_value=mock_yfinance_response(with_alerts=False))
    respx.get(
        re.compile(
            r"https://query[12]\.finance\.yahoo\.com/v7/finance/spark\?symbols=CSAN3\.SA,PRIO3\.SA,RDOR3\.SA,RAIL3\.SA,SBSP3\.SA,VIVT3\.SA,CMIG4\.SA,LREN3\.SA,CPLE6\.SA,UGPA3\.SA,ENEV3\.SA,TIMS3\.SA,TOTS3\.SA,EGIE3\.SA,HAPV3\.SA&range=1d&interval=15m"
        )
    ).mock(return_value=httpx.Response(200, json={"spark": {"result": []}}))

    assert variacao_subita.collect_and_save() is True

    import app.banco as app_banco

    app_banco._db_initialized = False
    app_banco.init_db()
    conn = get_connection()
    row = conn.execute(
        "SELECT payload FROM snapshots_paineis WHERE painel = 'variacao_subita' ORDER BY data_referencia DESC LIMIT 1"
    ).fetchone()
    conn.close()

    assert row is not None
    payload = json.loads(row["payload"])
    alertas = json.loads(payload["alertas_json"])
    assert len(alertas) == 0


def test_snapshot_contrato():
    save_variacao_subita_data(
        VariacaoSubitaData(
            timestamp=datetime(2026, 9, 28, 14, 0, tzinfo=timezone.utc),
            alertas_json=json.dumps([{"ticker": "PETR4", "change_percent": 2.5}]),
            fonte="yfinance",
        )
    )

    client = TestClient(app)
    response = client.get("/api/snapshot")
    assert response.status_code == 200

    data = response.json()
    assert "variacao_subita" in data["paineis"]
    panel = data["paineis"]["variacao_subita"]
    assert panel["fonte"] == "yfinance"
    assert panel["coletado_em"] == "2026-09-28T14:00:00+00:00"
    assert len(panel["alertas"]) == 1
    assert panel["alertas"][0]["ticker"] == "PETR4"
