import json
from unittest.mock import Mock
from app.collectors.concentracao_ordens import collect_and_save
from app.database import get_latest_concentracao_ordens_data, init_db


def test_concentracao_ordens_sucesso(monkeypatch):
    init_db()
    mock_response = Mock()
    mock_response.json.return_value = {
        "results": [
            {
                "symbol": "PETR4",
                "regularMarketVolume": 1000,
                "regularMarketPrice": 30.0,
                "regularMarketTrades": 10,
            },
            {
                "symbol": "VALE3",
                "regularMarketVolume": 500,
                "regularMarketPrice": 60.0,
                "regularMarketTrades": 20,
            },
        ]
    }
    monkeypatch.setattr(
        "app.collectors.brapi.cotacoes",
        lambda tickers: {res["symbol"]: res for res in mock_response.json()["results"]},
    )
    assert collect_and_save() is True
    data = get_latest_concentracao_ordens_data()
    assert data is not None
    assert data.fonte == "brapi"
    alertas = json.loads(data.alertas_json)
    assert len(alertas) == 2
    assert alertas[0]["ticker"] == "PETR4"
    assert alertas[0]["ticket_medio"] == 3000.0


def test_concentracao_ordens_sem_trades(monkeypatch):
    init_db()
    mock_response = Mock()
    mock_response.json.return_value = {
        "results": [
            {"symbol": "ITUB4", "regularMarketVolume": 1000, "regularMarketPrice": 30.0}
        ]
    }
    monkeypatch.setattr(
        "app.collectors.brapi.cotacoes",
        lambda tickers: {res["symbol"]: res for res in mock_response.json()["results"]},
    )
    assert collect_and_save() is True
    data = get_latest_concentracao_ordens_data()
    assert data is not None
    alertas = json.loads(data.alertas_json)
    assert len(alertas) == 0


# --------------------------------------------------------------------------
# MetaTrader 5: número de negócios vem do tick_volume da barra diária
# --------------------------------------------------------------------------

import httpx  # noqa: E402
import respx  # noqa: E402

from app.collectors import utils  # noqa: E402

MT5_BASE = "http://mt5.teste:8000/api/v1"


def _barra(close: float, real: int, ticks: int) -> dict:
    return {
        "time": "2026-11-04T00:00:00",
        "open": close,
        "high": close,
        "low": close,
        "close": close,
        "tick_volume": ticks,
        "spread": 1,
        "real_volume": real,
    }


@respx.mock
def test_concentracao_ordens_pelo_mt5(monkeypatch):
    init_db()
    monkeypatch.setenv("MT5_API_URL", MT5_BASE)
    monkeypatch.setattr(utils, "MIN_DELAY", 0.0)
    barras = {
        "PETR4": [_barra(30.0, 1000, 10)],  # ticket 3.000
        "VALE3": [_barra(60.0, 500, 20)],  # ticket 1.500
    }

    def responder(request: httpx.Request) -> httpx.Response:
        dados = barras.get(request.url.params["symbol"], [])
        if not dados:
            return httpx.Response(503, json={"detail": "símbolo indisponível"})
        return httpx.Response(200, json={"data": dados})

    respx.get(f"{MT5_BASE}/rates/from-pos").mock(side_effect=responder)
    yahoo = respx.get(url__regex=r"https://query[12]\.finance\.yahoo\.com.*")
    brapi = respx.get(url__startswith="https://brapi.dev")

    assert collect_and_save() is True

    assert not yahoo.called
    assert not brapi.called
    data = get_latest_concentracao_ordens_data()
    assert data is not None
    assert data.fonte == "mt5"
    alertas = json.loads(data.alertas_json)
    assert [a["ticker"] for a in alertas] == ["PETR4", "VALE3"]
    assert alertas[0]["ticket_medio"] == 3000.0
    assert alertas[0]["trades"] == 10


@respx.mock
def test_concentracao_ordens_ignora_simbolo_sem_volume_real(monkeypatch):
    """Sem real_volume, tick_volume é contagem de cotações, não de negócios."""
    init_db()
    monkeypatch.setenv("MT5_API_URL", MT5_BASE)
    monkeypatch.setattr(utils, "MIN_DELAY", 0.0)

    def responder(request: httpx.Request) -> httpx.Response:
        if request.url.params["symbol"] == "PETR4":
            return httpx.Response(200, json={"data": [_barra(30.0, 0, 999)]})
        return httpx.Response(503, json={"detail": "símbolo indisponível"})

    respx.get(f"{MT5_BASE}/rates/from-pos").mock(side_effect=responder)
    monkeypatch.setattr("app.collectors.brapi.cotacoes", lambda tickers: {})

    assert collect_and_save() is True
    data = get_latest_concentracao_ordens_data()
    assert data is not None
    assert json.loads(data.alertas_json) == []
