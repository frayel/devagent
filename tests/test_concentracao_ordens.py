import json

import httpx
import respx

from app.collectors import utils
from app.collectors.concentracao_ordens import calcular, collect_and_save
from app.database import get_latest_concentracao_ordens_data, init_db


def test_calcular_ordena_por_ticket_medio():
    alertas = calcular(
        [
            {
                "symbol": "VALE3",
                "regularMarketVolume": 500,
                "regularMarketPrice": 60.0,
                "regularMarketTrades": 20,
            },
            {
                "symbol": "PETR4",
                "regularMarketVolume": 1000,
                "regularMarketPrice": 30.0,
                "regularMarketTrades": 10,
            },
            # Sem número de negócios: fica de fora.
            {"symbol": "ITUB4", "regularMarketVolume": 1000, "regularMarketPrice": 30},
        ]
    )
    assert [a["ticker"] for a in alertas] == ["PETR4", "VALE3"]
    assert alertas[0]["ticket_medio"] == 3000.0


def test_concentracao_ordens_sem_mt5_fica_vazio():
    """Sem o MT5 não há número de negócios: o painel mostra Dados indisponíveis."""
    init_db()
    assert collect_and_save() is True
    data = get_latest_concentracao_ordens_data()
    assert data is not None
    assert json.loads(data.alertas_json) == []


# --------------------------------------------------------------------------
# MetaTrader 5: número de negócios vem do tick_volume da barra diária
# --------------------------------------------------------------------------

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

    assert collect_and_save() is True

    assert not yahoo.called
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

    assert collect_and_save() is True
    data = get_latest_concentracao_ordens_data()
    assert data is not None
    assert json.loads(data.alertas_json) == []
