"""MetaTrader 5 como fonte preferencial (app/collectors/mt5.py)."""

from datetime import datetime, timedelta, timezone

import httpx
import pytest
import respx

from app.collectors import mt5, utils
from app.collectors.utils import fetch_with_retry

BASE = "http://mt5.teste:8000/api/v1"
RATES = f"{BASE}/rates/from-pos"
CHAVE = "chave-de-teste"


@pytest.fixture
def mt5_ligado(monkeypatch):
    monkeypatch.setenv("MT5_API_URL", BASE + "/")
    monkeypatch.setenv("MT5_API_KEY", CHAVE)
    monkeypatch.setattr(utils, "MIN_DELAY", 0.0)
    yield


def barras_diarias(n: int, inicio: float = 10.0, fim: datetime | None = None):
    """n pregões terminando em `fim`, no formato JSON da mt5api."""
    fim = fim or datetime(2026, 10, 5)
    dias = []
    d = fim
    while len(dias) < n:
        if d.weekday() < 5:
            dias.append(d)
        d -= timedelta(days=1)
    dias.reverse()
    return [
        {
            "time": d.isoformat(),
            "open": inicio + i,
            "high": inicio + i + 0.5,
            "low": inicio + i - 0.5,
            "close": inicio + i + 0.25,
            "tick_volume": 10,
            "spread": 1,
            "real_volume": 1000 + i,
        }
        for i, d in enumerate(dias)
    ]


def rota_rates(dados_por_simbolo: dict[str, list[dict]]):
    def responder(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("X-API-Key") == CHAVE
        simbolo = request.url.params["symbol"]
        tf = request.url.params["timeframe"]
        dados = dados_por_simbolo.get(f"{simbolo}:{tf}", [])
        return httpx.Response(200, json={"data": dados, "count": len(dados)})

    return respx.get(RATES).mock(side_effect=responder)


def test_sem_configuracao_nao_intercepta():
    assert not mt5.configurado()
    url = "https://query1.finance.yahoo.com/v7/finance/spark?symbols=PETR4.SA"
    assert mt5.interceptar(url) is None


def test_traducao_de_simbolos(monkeypatch):
    assert mt5.simbolo_mt5("PETR4.SA") == "PETR4"
    assert mt5.simbolo_mt5("^BVSP") == "IBOV"
    assert mt5.simbolo_mt5("BRL=X") == "DOL$"
    assert mt5.simbolo_mt5("^GSPC") is None
    monkeypatch.setenv("MT5_SIMBOLOS", '{"^BVSP": "IBOV11", "BRL=X": "USDBRL"}')
    assert mt5.simbolo_mt5("^BVSP") == "IBOV11"
    assert mt5.simbolo_mt5("BRL=X") == "USDBRL"


@respx.mock
def test_spark_servido_pelo_mt5(mt5_ligado):
    rota = rota_rates(
        {
            "PETR4:D1": barras_diarias(30, 30.0),
            "VALE3:D1": barras_diarias(30, 60.0),
        }
    )
    yahoo = respx.get(url__startswith="https://query1.finance.yahoo.com")

    url = (
        "https://query1.finance.yahoo.com/v7/finance/spark"
        "?symbols=PETR4.SA,VALE3.SA&range=5d&interval=1d"
    )
    resp = fetch_with_retry(url)

    assert not yahoo.called
    assert rota.call_count == 2
    assert resp.headers["X-Fonte"] == "mt5"
    resultado = resp.json()["spark"]["result"]
    assert [r["symbol"] for r in resultado] == ["PETR4.SA", "VALE3.SA"]

    bloco = resultado[0]["response"][0]
    quote = bloco["indicators"]["quote"][0]
    assert len(quote["close"]) == 5
    assert quote["close"][-1] == 30.0 + 29 + 0.25
    assert quote["volume"][-1] == 1029
    # Fechamento anterior à janela, como o Yahoo faz.
    assert bloco["meta"]["chartPreviousClose"] == 30.0 + 24 + 0.25
    assert bloco["meta"]["previousClose"] == 30.0 + 28 + 0.25
    assert bloco["meta"]["regularMarketPrice"] == quote["close"][-1]
    # Candle diário às 13:00 UTC: a data é a mesma em UTC e em BRT.
    ultimo = datetime.fromtimestamp(bloco["timestamp"][-1], tz=timezone.utc)
    assert ultimo.strftime("%Y-%m-%d %H:%M") == "2026-10-05 13:00"
    assert ultimo.astimezone(timezone(timedelta(hours=-3))).date().day == 5


@respx.mock
def test_cache_evita_segunda_chamada(mt5_ligado):
    rota = rota_rates({"PETR4:D1": barras_diarias(30)})
    url = "https://query1.finance.yahoo.com/v7/finance/spark?symbols=PETR4.SA&range=1d&interval=1d"
    fetch_with_retry(url)
    fetch_with_retry(url.replace("range=1d", "range=1mo"))
    assert rota.call_count == 1


@respx.mock
def test_chart_do_ibovespa_com_janela_de_um_mes(mt5_ligado):
    rota_rates({"IBOV:D1": barras_diarias(260, 150000.0)})
    url = (
        "https://query2.finance.yahoo.com/v8/finance/chart/^BVSP?range=1mo&interval=1d"
    )
    resp = fetch_with_retry(url)
    bloco = resp.json()["chart"]["result"][0]
    n = len(bloco["timestamp"])
    assert 20 <= n <= 23
    assert bloco["meta"]["symbol"] == "^BVSP"
    assert bloco["meta"]["simboloMt5"] == "IBOV"


@respx.mock
def test_intradia_converte_fuso_do_servidor(mt5_ligado):
    m15 = []
    for i in range(4):
        h = datetime(2026, 10, 5, 10, 0) + timedelta(minutes=15 * i)
        m15.append(
            {"time": h.isoformat(), "open": 1, "high": 1, "low": 1, "close": 1 + i}
        )
    m15.insert(
        0, {"time": "2026-10-02T17:45:00", "open": 1, "high": 1, "low": 1, "close": 9}
    )
    rota_rates({"PETR4:D1": barras_diarias(10), "PETR4:M15": m15})
    url = "https://query1.finance.yahoo.com/v7/finance/spark?symbols=PETR4.SA&range=1d&interval=15m"
    bloco = fetch_with_retry(url).json()["spark"]["result"][0]["response"][0]
    assert bloco["indicators"]["quote"][0]["close"] == [1, 2, 3, 4]
    primeiro = datetime.fromtimestamp(bloco["timestamp"][0], tz=timezone.utc)
    assert primeiro.strftime("%H:%M") == "13:00"  # 10:00 BRT


@respx.mock
def test_mt5_fora_do_ar_cai_para_o_yahoo_e_pausa(mt5_ligado):
    rota = respx.get(RATES).mock(side_effect=httpx.ConnectError("recusado"))
    yahoo = respx.get(url__startswith="https://query1.finance.yahoo.com").mock(
        return_value=httpx.Response(200, json={"spark": {"result": []}})
    )
    url = "https://query1.finance.yahoo.com/v7/finance/spark?symbols=PETR4.SA,VALE3.SA&range=1d&interval=1d"
    fetch_with_retry(url)
    fetch_with_retry(url)
    assert yahoo.call_count == 2
    # Depois da primeira falha o servidor fica em pausa: uma tentativa só.
    assert rota.call_count == 1
    assert mt5.fonte_efetiva("yfinance") == "yfinance"


@respx.mock
def test_chave_recusada_cai_para_o_yahoo(mt5_ligado):
    respx.get(RATES).mock(return_value=httpx.Response(401, json={"detail": "x"}))
    yahoo = respx.get(url__startswith="https://query2.finance.yahoo.com").mock(
        return_value=httpx.Response(200, json={"chart": {"result": []}})
    )
    fetch_with_retry(
        "https://query2.finance.yahoo.com/v8/finance/chart/^BVSP?range=1y&interval=1d"
    )
    assert yahoo.called


@respx.mock
def test_simbolo_sem_traducao_vai_ao_yahoo(mt5_ligado):
    rota = respx.get(RATES)
    yahoo = respx.get(url__startswith="https://query1.finance.yahoo.com").mock(
        return_value=httpx.Response(200, json={"spark": {"result": []}})
    )
    fetch_with_retry(
        "https://query1.finance.yahoo.com/v7/finance/spark?symbols=%5EGSPC&range=2mo&interval=1d"
    )
    assert yahoo.called
    assert not rota.called


@respx.mock
def test_modo_exclusivo_nao_recorre_ao_yahoo(mt5_ligado):
    respx.get(RATES).mock(return_value=httpx.Response(200, json={"data": []}))
    yahoo = respx.get(url__startswith="https://query2.finance.yahoo.com")
    with mt5.exclusivo():
        with pytest.raises(httpx.HTTPError):
            fetch_with_retry(
                "https://query2.finance.yahoo.com/v8/finance/chart/^BVSP?range=1y&interval=1d"
            )
    assert not yahoo.called


def test_rotulo_de_fonte():
    assert mt5.fonte_efetiva("yfinance") == "yfinance"
    mt5.registrar_fonte("mt5")
    assert mt5.fonte_efetiva("yfinance") == "mt5"
    mt5.registrar_fonte("yfinance")
    assert mt5.fonte_efetiva("yfinance") == "mt5+yfinance"
    mt5.reiniciar_rastreio()
    assert mt5.fonte_efetiva("yfinance") == "yfinance"


@respx.mock
def test_ibovespa_prefere_mt5_a_brapi(mt5_ligado, monkeypatch):
    from app.collectors.ibovespa import collect_and_save
    from app.database import get_latest_ibovespa_data

    monkeypatch.setenv("BRAPI_TOKEN", "tok")
    rota_rates({"IBOV:D1": barras_diarias(260, 150000.0)})
    brapi = respx.get(url__startswith="https://brapi.dev")

    assert collect_and_save()
    assert not brapi.called
    dado = get_latest_ibovespa_data()
    assert dado is not None
    assert dado.fonte == "mt5"
    assert dado.current_price == 150000.0 + 259 + 0.25
    assert dado.mm200 is not None


@respx.mock
def test_ibovespa_sem_mt5_segue_para_brapi(mt5_ligado, monkeypatch):
    from app.collectors import ibovespa

    monkeypatch.setenv("BRAPI_TOKEN", "tok")
    respx.get(RATES).mock(side_effect=httpx.ConnectError("recusado"))
    chamado = []

    def falso_brapi():
        chamado.append(True)
        return None

    monkeypatch.setattr(ibovespa, "fetch_brapi", falso_brapi)
    monkeypatch.setattr(ibovespa, "fetch_yfinance", lambda: None)
    assert not ibovespa.collect_and_save()
    assert chamado


@respx.mock
def test_simbolo_recusado_nao_pausa_os_outros(mt5_ligado, caplog):
    """503 da mt5api é falha do símbolo (Mt5RuntimeError), não do servidor."""
    erro = {
        "type": "/errors/mt5-error",
        "title": "MT5 Terminal Error",
        "status": 503,
        "detail": "MT5 last status: (-4, 'Terminal: Not found')",
    }

    def responder(request: httpx.Request) -> httpx.Response:
        if request.url.params["symbol"] == "ELET3":
            return httpx.Response(503, json=erro)
        return httpx.Response(200, json={"data": barras_diarias(30)})

    rota = respx.get(RATES).mock(side_effect=responder)
    url = (
        "https://query1.finance.yahoo.com/v7/finance/spark"
        "?symbols=ELET3.SA,PETR4.SA,VALE3.SA&range=5d&interval=1d"
    )
    with caplog.at_level("WARNING"):
        resultado = fetch_with_retry(url).json()["spark"]["result"]
    assert [r["symbol"] for r in resultado] == ["PETR4.SA", "VALE3.SA"]
    assert "Not found" in caplog.text

    # Na rodada seguinte o símbolo recusado não é pedido de novo.
    mt5._cache.clear()
    fetch_with_retry(url)
    pedidos = [c.request.url.params["symbol"] for c in rota.calls]
    assert pedidos.count("ELET3") == 1
    assert pedidos.count("PETR4") == 2


@respx.mock
def test_pausa_informa_o_motivo(mt5_ligado):
    respx.get(RATES).mock(side_effect=httpx.ConnectTimeout("lento"))
    with pytest.raises(mt5.Mt5Indisponivel):
        mt5.barras("PETR4", "D1")
    with pytest.raises(mt5.Mt5Indisponivel, match="ConnectTimeout"):
        mt5.barras("VALE3", "D1")
