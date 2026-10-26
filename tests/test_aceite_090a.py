import respx
import httpx
from datetime import datetime, timezone
from app.collectors import utils, registro_fontes
from app.services import sistema


def test_falha_detalhada_com_mascara():
    registro_fontes.limpar()
    url = "https://query2.finance.yahoo.com/v8/finance/chart/PETZ3.SA?range=2y&interval=1d&token=secreto"
    corpo_resposta = '{"error": "Not Found", "token": "supersecreto", "apikey": "1234"}'

    with respx.mock:
        respx.get(url).respond(status_code=404, text=corpo_resposta)
        client = httpx.Client()
        try:
            utils.fetch_with_retry(url, client=client, max_retries=1)
        except Exception:
            pass

    fontes = registro_fontes.fontes()
    fonte = fontes["Yahoo Finance"]

    assert getattr(fonte, "ultimo_erro", None) is not None
    assert "token=***" in fonte.ultimo_erro

    # Check endpoints
    ep = "/v8/finance/chart/{simbolo}"
    assert ep in getattr(fonte, "endpoints", {})
    ep_data = fonte.endpoints[ep]

    assert ep_data["falhas"] == 1
    assert ep_data["ultimo_status"] == 404

    assert '"token": "***"' in ep_data["ultimo_corpo"]
    assert '"apikey": "***"' in ep_data["ultimo_corpo"]


def test_nivel_problema_vs_atencao():
    registro_fontes.limpar()

    # 1. 404 isolado
    url1 = "https://query2.finance.yahoo.com/v8/finance/chart/WEGE3.SA"
    with respx.mock:
        respx.get(url1).respond(status_code=404, text="Not Found")
        client = httpx.Client()
        try:
            utils.fetch_with_retry(url1, client=client, max_retries=1)
        except Exception:
            pass

    item = sistema._item_da_fonte(
        "Yahoo Finance",
        registro_fontes.fontes()["Yahoo Finance"],
        "",
        datetime.now(timezone.utc),
    )
    assert item.nivel == sistema.ATENCAO

    # 2. Endpoint inteiro caindo (simboliza 3 falhas de um simbolo já conhecido ok)
    url_ok = "https://query2.finance.yahoo.com/v8/finance/chart/^BVSP"
    url2 = "https://query2.finance.yahoo.com/v8/finance/chart/PETR4.SA"
    url3 = "https://query2.finance.yahoo.com/v8/finance/chart/VALE3.SA"

    with respx.mock:
        respx.get(url_ok).mock(
            side_effect=[
                httpx.Response(200, text="OK"),
                httpx.Response(404, text="Not Found"),
            ]
        )
        respx.get(url2).respond(status_code=404, text="Not Found")
        respx.get(url3).respond(status_code=404, text="Not Found")

        client = httpx.Client()
        utils.fetch_with_retry(url_ok, client=client)  # ok
        try:
            utils.fetch_with_retry(url_ok, client=client, max_retries=1)  # fail 1
        except Exception:
            pass
        try:
            utils.fetch_with_retry(url2, client=client, max_retries=1)  # fail 2
        except Exception:
            pass
        try:
            utils.fetch_with_retry(url3, client=client, max_retries=1)  # fail 3
        except Exception:
            pass

    item = sistema._item_da_fonte(
        "Yahoo Finance",
        registro_fontes.fontes()["Yahoo Finance"],
        "",
        datetime.now(timezone.utc),
    )
    assert item.nivel == sistema.PROBLEMA
    assert "parece ter mudado ou saído do ar" in item.detalhe
