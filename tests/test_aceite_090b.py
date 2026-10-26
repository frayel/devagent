import httpx
import respx
from app.banco import init_db, is_simbolo_suspenso
from app.collectors.utils import fetch_historico_diario_yfinance_spark, simbolo_yahoo


def test_fetch_lote_divide():
    init_db()
    symbols = ["PETR4", "VALE3", "SOMA3", "NTCO3"]
    client = httpx.Client()

    def on_request(request):
        url = str(request.url)
        if "SOMA3" in url or "NTCO3" in url:
            return httpx.Response(404, json={"error": "Not found"})
        else:
            return httpx.Response(
                200,
                json={
                    "spark": {
                        "result": [{"symbol": "PETR4.SA"}, {"symbol": "VALE3.SA"}]
                    }
                },
            )

    with respx.mock:
        respx.get(
            url__startswith="https://query1.finance.yahoo.com/v8/finance/spark"
        ).mock(side_effect=on_request)
        respx.get(
            url__startswith="https://query2.finance.yahoo.com/v8/finance/spark"
        ).mock(side_effect=on_request)
        respx.get(
            url__startswith="https://query1.finance.yahoo.com/v8/finance/chart"
        ).mock(return_value=httpx.Response(404, json={"error": "Not found"}))
        respx.get(
            url__startswith="https://query2.finance.yahoo.com/v8/finance/chart"
        ).mock(return_value=httpx.Response(404, json={"error": "Not found"}))

        results = fetch_historico_diario_yfinance_spark(symbols, "1d", "15m", client)

        assert len(results) == 2

        fetch_historico_diario_yfinance_spark(symbols, "1d", "15m", client)
        fetch_historico_diario_yfinance_spark(symbols, "1d", "15m", client)

        assert is_simbolo_suspenso("yfinance", "SOMA3")


def test_simbolo():
    assert simbolo_yahoo("^BVSP") == "^BVSP"
    assert simbolo_yahoo("BRL=X") == "BRL=X"
    assert simbolo_yahoo("PETR4") == "PETR4.SA"


def test_teto_de_chamadas():
    init_db()
    symbols = [f"TICK{i}" for i in range(1, 91)]
    symbols[15] = "INVALIDO1"
    symbols[16] = "INVALIDO2"

    client = httpx.Client()
    chamadas = []

    def on_request(request):
        chamadas.append(request)
        url = str(request.url)
        if "INVALIDO" in url:
            return httpx.Response(404, json={"error": "Not found"})
        return httpx.Response(200, json={"spark": {"result": []}})

    with respx.mock:
        respx.get(
            url__startswith="https://query1.finance.yahoo.com/v8/finance/spark"
        ).mock(side_effect=on_request)
        respx.get(
            url__startswith="https://query2.finance.yahoo.com/v8/finance/spark"
        ).mock(side_effect=on_request)
        respx.get(
            url__startswith="https://query1.finance.yahoo.com/v8/finance/chart"
        ).mock(return_value=httpx.Response(404, json={"error": "Not found"}))
        respx.get(
            url__startswith="https://query2.finance.yahoo.com/v8/finance/chart"
        ).mock(return_value=httpx.Response(404, json={"error": "Not found"}))

        fetch_historico_diario_yfinance_spark(symbols, "1d", "15m", client)

        assert len(chamadas) <= 6 + 10
