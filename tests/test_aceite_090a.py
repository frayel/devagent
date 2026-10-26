import pytest
from fastapi.testclient import TestClient
from app.main import app
import respx
from app.collectors import utils, registro_fontes
from app.main import estado_do_sistema
from app.services.sistema import PROBLEMA, ATENCAO


@pytest.fixture(autouse=True)
def clean_registro():
    registro_fontes.limpar()


def test_falha_salva_corpo_sem_token():
    with respx.mock:
        respx.get(
            "https://query1.finance.yahoo.com/v8/finance/chart/AAPL?token=abc"
        ).respond(404, text="Error with token=abc")
        try:
            utils.fetch_with_retry(
                "https://query1.finance.yahoo.com/v8/finance/chart/AAPL?token=abc",
                max_retries=1,
            )
        except Exception:
            pass

    fontes = registro_fontes.fontes()
    assert "Yahoo Finance" in fontes
    yahoo = fontes["Yahoo Finance"]
    assert (
        yahoo.ultimo_erro
        == "HTTP 404 em https://query1.finance.yahoo.com/v8/finance/chart/AAPL?token=***"
    )

    ep = yahoo.endpoints["/v8/finance/chart/{simbolo}"]
    assert ep.ultimo_status == 404
    assert ep.ultimo_corpo == "Error with token=***"
    assert "AAPL" in ep.falhas_seguidas[-1][0]


def test_problema_por_sequencia_de_404_simbolos_distintos():
    yahoo_nome = "Yahoo Finance"
    registro_fontes.sucesso(
        yahoo_nome, url="https://query1.finance.yahoo.com/v8/finance/chart/BVSP"
    )

    registro_fontes.falha(
        yahoo_nome,
        "Erro",
        url="https://query1.finance.yahoo.com/v8/finance/chart/AAPL",
        status=404,
        corpo="na",
    )
    registro_fontes.falha(
        yahoo_nome,
        "Erro",
        url="https://query1.finance.yahoo.com/v8/finance/chart/MSFT",
        status=404,
        corpo="na",
    )
    registro_fontes.falha(
        yahoo_nome,
        "Erro",
        url="https://query1.finance.yahoo.com/v8/finance/chart/BVSP",
        status=404,
        corpo="na",
    )

    sys_estado = estado_do_sistema()
    grupos = [g for g in sys_estado["grupos"] if g["titulo"] == "Integrações externas"][
        0
    ]
    yahoo_item = [i for i in grupos["itens"] if i["nome"] == "Yahoo Finance"][0]

    assert yahoo_item["nivel"] == PROBLEMA
    assert (
        "parece ter mudado ou saído do ar" in yahoo_item["resumo"]
        or "parece ter mudado ou saído do ar" in yahoo_item["detalhe"]
        or "parece ter mudado ou saído do ar" in str(sys_estado)
    )


def test_atencao_por_404_isolado():
    yahoo_nome = "Yahoo Finance"
    registro_fontes.falha(
        yahoo_nome,
        "Erro",
        url="https://query1.finance.yahoo.com/v8/finance/chart/VALE3.SA",
        status=404,
        corpo="na",
    )

    sys_estado = estado_do_sistema()
    grupos = [g for g in sys_estado["grupos"] if g["titulo"] == "Integrações externas"][
        0
    ]
    yahoo_item = [i for i in grupos["itens"] if i["nome"] == "Yahoo Finance"][0]

    assert yahoo_item["nivel"] == ATENCAO
    assert "VALE3.SA" in yahoo_item["detalhe"]


def test_api_sistema_sem_segredos():
    with respx.mock:
        respx.get(
            "https://query1.finance.yahoo.com/v8/finance/chart/TEST?apikey=secret_123"
        ).respond(404, text="Leak apikey=secret_123 here")
        try:
            utils.fetch_with_retry(
                "https://query1.finance.yahoo.com/v8/finance/chart/TEST?apikey=secret_123",
                max_retries=1,
            )
        except Exception:
            pass

    client = TestClient(app)
    resp = client.get("/api/sistema")
    assert resp.status_code == 200
    assert "secret_123" not in resp.text
