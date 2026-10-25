import pytest
import httpx
from datetime import datetime, timezone
from app.collectors import utils
from app.collectors import registro_fontes
from app.services import sistema as s_sistema
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_fontes():
    registro_fontes.limpar()
    yield
    registro_fontes.limpar()


def test_falha_404_salva_campos_e_mascara_secrets(respx_mock):
    respx_mock.get(
        "https://query2.finance.yahoo.com/v8/finance/chart/PETR4.SA?range=1d&interval=1d&token=secret123"
    ).mock(
        return_value=httpx.Response(
            404,
            text='{"error": "Not Found", "apikey": "secret123", "token": "secret123"}',
        )
    )

    with pytest.raises(httpx.HTTPStatusError):
        utils.fetch_with_retry(
            "https://query2.finance.yahoo.com/v8/finance/chart/PETR4.SA?range=1d&interval=1d&token=secret123",
            client=None,
            max_retries=1,
        )

    fontes = registro_fontes.fontes()
    yahoo = fontes.get("Yahoo Finance")
    assert yahoo is not None
    assert len(yahoo.falhas_recentes) == 1
    falha = yahoo.falhas_recentes[0]

    assert falha.endpoint == "/v8/finance/chart/{simbolo}"
    assert "PETR4" in falha.simbolos
    assert falha.status == 404
    assert (
        "token=***" in falha.corpo
        or "token: ***" in falha.corpo
        or 'apikey": "***"' in falha.corpo
        or 'apikey": "***' in falha.corpo
        or "***" in falha.corpo
    )


def test_regra_de_nivel_atencao_vs_problema(respx_mock):
    # Simular 3 falhas seguidas no mesmo endpoint, símbolos diferentes, incluindo ^BVSP
    simbolos = ["VALE3.SA", "ITUB4.SA", "^BVSP"]
    for s in simbolos:
        url = f"https://query2.finance.yahoo.com/v8/finance/chart/{s}?range=1d&interval=1d"
        respx_mock.get(url).mock(return_value=httpx.Response(404, text="Not Found"))
        try:
            utils.fetch_with_retry(url, client=None, max_retries=1)
        except httpx.HTTPStatusError:
            pass

    agora = datetime.now(timezone.utc)
    fontes = registro_fontes.fontes()

    itens = s_sistema.verificar_integracoes(fontes, None, {}, agora)
    item_yahoo = next(i for i in itens if i.nome == "Yahoo Finance")

    # Deve ser PROBLEMA porque tem 3 seguidos e inclui ^BVSP
    assert item_yahoo.nivel == s_sistema.PROBLEMA
    assert "parece ter mudado ou saído do ar" in item_yahoo.detalhe


def test_regra_de_nivel_atencao_isolada(respx_mock):
    # Simular falha isolada de apenas 1 ou 2 ativos, ou que não inclui ^BVSP
    simbolos = ["VALE3.SA"]
    for s in simbolos:
        url = f"https://query2.finance.yahoo.com/v8/finance/chart/{s}?range=1d&interval=1d"
        respx_mock.get(url).mock(return_value=httpx.Response(404, text="Not Found"))
        try:
            utils.fetch_with_retry(url, client=None, max_retries=1)
        except httpx.HTTPStatusError:
            pass

    agora = datetime.now(timezone.utc)
    fontes = registro_fontes.fontes()

    itens = s_sistema.verificar_integracoes(fontes, None, {}, agora)
    item_yahoo = next(i for i in itens if i.nome == "Yahoo Finance")

    # Falha isolada de 404 = ATENCAO
    assert item_yahoo.nivel == s_sistema.ATENCAO
    assert "Falhas 404 em: VALE3" in item_yahoo.detalhe


def test_nenhum_segredo_no_snapshot(respx_mock):
    # Insere falha com segredo e chama o snapshot da api e pagina html
    respx_mock.get(
        "https://query2.finance.yahoo.com/v8/finance/chart/PETR4.SA?range=1d&interval=1d&token=secret_val"
    ).mock(
        return_value=httpx.Response(
            404, text='{"error": "Not Found", "token": "secret_val"}'
        )
    )
    try:
        utils.fetch_with_retry(
            "https://query2.finance.yahoo.com/v8/finance/chart/PETR4.SA?range=1d&interval=1d&token=secret_val",
            client=None,
            max_retries=1,
        )
    except httpx.HTTPStatusError:
        pass

    resp_api = client.get("/api/sistema")
    assert resp_api.status_code == 200
    assert "secret_val" not in resp_api.text

    resp_html = client.get("/sistema")
    assert resp_html.status_code == 200
    assert "secret_val" not in resp_html.text
