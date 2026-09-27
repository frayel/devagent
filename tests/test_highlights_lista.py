import json

import httpx
import respx

from app.collectors.highlights import LISTA_URL, fetch_brapi_lista


def _lista(n: int) -> dict:
    return {
        "stocks": [
            {
                "stock": f"ATIV{i}",
                "close": 10.0 + i,
                "change": i - n / 2,
                "type": "stock",
            }
            for i in range(n)
        ]
    }


@respx.mock
def test_lista_brapi_monta_ranking(monkeypatch):
    monkeypatch.delenv("BRAPI_TOKEN", raising=False)
    respx.get(LISTA_URL).respond(200, json=_lista(20))
    data = fetch_brapi_lista()
    assert data is not None
    altas = json.loads(data.highs_json)
    baixas = json.loads(data.lows_json)
    assert [a["ticker"] for a in altas] == [
        "ATIV19",
        "ATIV18",
        "ATIV17",
        "ATIV16",
        "ATIV15",
    ]
    assert [b["ticker"] for b in baixas] == [
        "ATIV0",
        "ATIV1",
        "ATIV2",
        "ATIV3",
        "ATIV4",
    ]
    assert data.fonte == "brapi"


@respx.mock
def test_lista_brapi_com_poucos_ativos_cai_no_plano_b(monkeypatch):
    monkeypatch.delenv("BRAPI_TOKEN", raising=False)
    respx.get(LISTA_URL).respond(200, json=_lista(3))
    assert fetch_brapi_lista() is None


@respx.mock
def test_lista_brapi_fora_do_ar(monkeypatch):
    monkeypatch.delenv("BRAPI_TOKEN", raising=False)
    monkeypatch.setattr("app.collectors.utils.time.sleep", lambda s: None)
    respx.get(LISTA_URL).mock(side_effect=httpx.ConnectError("fora"))
    assert fetch_brapi_lista() is None
