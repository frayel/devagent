import json
from app.collectors import faca_caindo
from datetime import datetime, timezone


def test_fetch_yfinance_success(monkeypatch):
    def mock_fetch(symbols, *args, **kwargs):
        res = []
        if "PETR4" in symbols:
            res.append(
                {
                    "symbol": "PETR4.SA",
                    "response": [
                        {"indicators": {"quote": [{"close": [10.0, 9.0, 8.0, 7.0]}]}}
                    ],
                }
            )
        if "VALE3" in symbols:
            res.append(
                {
                    "symbol": "VALE3.SA",
                    "response": [
                        {"indicators": {"quote": [{"close": [10.0, 11.0, 9.0, 10.0]}]}}
                    ],
                }
            )
        return res

    monkeypatch.setattr(
        "app.collectors.faca_caindo.fetch_historico_diario_yfinance_spark", mock_fetch
    )
    monkeypatch.setattr("app.collectors.faca_caindo.TICKERS", ["PETR4", "VALE3"])

    data = faca_caindo.fetch_yfinance()
    assert data is not None
    assert data.fonte == "yfinance"
    alertas = json.loads(data.alertas_json)
    assert len(alertas) == 1
    assert alertas[0]["ticker"] == "PETR4"
    assert alertas[0]["dias"] == 3
    assert alertas[0]["variacao_acumulada"] < 0


def test_fetch_yfinance_empty(monkeypatch):
    def mock_fetch(*args, **kwargs):
        return []

    monkeypatch.setattr(
        "app.collectors.faca_caindo.fetch_historico_diario_yfinance_spark", mock_fetch
    )
    monkeypatch.setattr("app.collectors.faca_caindo.TICKERS", ["PETR4", "VALE3"])

    data = faca_caindo.fetch_yfinance()
    assert data is None


def test_collect_and_save_success(monkeypatch):
    monkeypatch.setattr(
        faca_caindo,
        "fetch_yfinance",
        lambda: faca_caindo.FacaCaindoData(
            timestamp=datetime.now(timezone.utc), alertas_json="[]", fonte="yfinance"
        ),
    )
    saved = False

    def mock_save(data):
        nonlocal saved
        saved = True

    monkeypatch.setattr(faca_caindo, "save_faca_caindo_data", mock_save)

    assert faca_caindo.collect_and_save() is True
    assert saved is True


def test_view_le_os_campos_que_o_coletor_grava(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app as fastapi_app
    from app.database import init_db, save_faca_caindo_data

    import app.banco

    app.banco._db_initialized = False
    init_db()

    data = faca_caindo.FacaCaindoData(
        timestamp=datetime.now(timezone.utc),
        alertas_json=json.dumps(
            [
                {
                    "ticker": "BBAS3",
                    "dias": 4,
                    "variacao_acumulada": -8.5,
                }
            ]
        ),
        fonte="yfinance",
    )
    save_faca_caindo_data(data)

    client = TestClient(fastapi_app)
    response = client.get("/")
    assert response.status_code == 200
    html = response.text

    assert "BBAS3" in html
    assert "4" in html
