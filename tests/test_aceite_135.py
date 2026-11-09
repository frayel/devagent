from datetime import datetime, timezone
import json
import pytest
import respx
from fastapi.testclient import TestClient

from devagent.aceite import exigir_spec_done
from app.collectors.highlights import (
    fetch_yfinance,
)
from app.collectors.utils import fechamento_anterior
from app.database import save_highlights_data
from app.main import app
from app.services.highlights import get_highlights_view_data
from tests.yahoo_falso import _fechamentos, _resultado
from tests.test_fronteira_chart_previous_close import (
    test_fronteira_chart_previous_close_coletores_reais,
    test_fronteira_chart_previous_close_falha_em_coletor_invalido,
)

client = TestClient(app)
SPARK = r"https://query[12]\.finance\.yahoo\.com/v8/finance/spark.*"


@pytest.fixture(autouse=True)
def spec_135_done():
    exigir_spec_done("135")


def criar_item_spark(
    simbolo: str,
    closes: list[float],
    preco: float,
    chart_prev: float,
    prev_close: float | None = None,
    timestamps: list[int] | None = None,
) -> dict:
    meta = {
        "regularMarketPrice": preco,
        "chartPreviousClose": chart_prev,
    }
    if prev_close is not None:
        meta["previousClose"] = prev_close
        meta["regularMarketPreviousClose"] = prev_close

    if timestamps is None:
        agora = int(datetime.now(timezone.utc).timestamp())
        timestamps = [agora - (len(closes) - 1 - i) * 86400 for i in range(len(closes))]

    return {
        "symbol": f"{simbolo}.SA",
        "response": [
            {
                "meta": meta,
                "timestamp": timestamps,
                "indicators": {
                    "quote": [
                        {
                            "close": closes,
                            "open": closes,
                            "high": closes,
                            "low": closes,
                            "volume": [1000] * len(closes),
                        }
                    ]
                },
            }
        ],
    }


@respx.mock
def test_criterio_1_spark_15d_penultimo_e_preco(monkeypatch):
    """Dado um spark de 15 dias com penúltimo fechamento 10.00, preço 10.50 e chartPreviousClose = 8.00:
    o change_percent do ativo é +5.00 (e não +31.25).
    """
    monkeypatch.setattr("app.collectors.highlights.TICKERS", ["PETR4"])
    monkeypatch.setattr("app.collectors.utils.time.sleep", lambda s: None)

    # 15 fechamentos terminando em 10.00 e 10.50
    closes = [8.00] * 13 + [10.00, 10.50]
    item = criar_item_spark("PETR4", closes, preco=10.50, chart_prev=8.00)

    respx.get(url__regex=SPARK).respond(200, json={"spark": {"result": [item]}})

    data = fetch_yfinance()
    assert data is not None

    highs = json.loads(data.highs_json)
    assert len(highs) == 1
    petr4 = highs[0]
    assert petr4["ticker"] == "PETR4"
    assert petr4["change_percent"] == pytest.approx(5.00, abs=0.01)
    assert petr4["change_percent"] != pytest.approx(31.25, abs=0.01)


@respx.mock
def test_criterio_2_dispersao_e_contagens_up_down(monkeypatch):
    """Com 3 ativos que sobem no dia mas estão abaixo do nível de 15 dias atrás,
    e 2 que caem no dia mas estão acima dele, up_count == 3, down_count == 2 e a Dispersão é 60%.
    """
    tickers = ["ALTA1", "ALTA2", "ALTA3", "QUEDA1", "QUEDA2"]
    monkeypatch.setattr("app.collectors.highlights.TICKERS", tickers)
    monkeypatch.setattr("app.collectors.utils.time.sleep", lambda s: None)

    results = []
    # 3 ativos que sobem hoje (+4%, +2%, +3%), mas estão abaixo de 15 dias atrás (100.0):
    for i, t in enumerate(["ALTA1", "ALTA2", "ALTA3"]):
        # 15 dias atrás = 100.0, penúltimo = 50.0, hoje = 52.0 (+4% hoje, -48% na janela)
        c = [100.0] * 13 + [50.0 + i, 52.0 + i]
        results.append(criar_item_spark(t, c, preco=52.0 + i, chart_prev=100.0))

    # 2 ativos que caem hoje (-2.5%, -2.2%), mas estão acima de 15 dias atrás (20.0):
    for i, t in enumerate(["QUEDA1", "QUEDA2"]):
        # 15 dias atrás = 20.0, penúltimo = 80.0, hoje = 78.0 (-2.5% hoje, +290% na janela)
        c = [20.0] * 13 + [80.0 + i, 78.0 + i]
        results.append(criar_item_spark(t, c, preco=78.0 + i, chart_prev=20.0))

    respx.get(url__regex=SPARK).respond(200, json={"spark": {"result": results}})

    data = fetch_yfinance()
    assert data is not None
    assert data.up_count == 3
    assert data.down_count == 2
    assert data.total_count == 5

    save_highlights_data(data)
    view_data = get_highlights_view_data()
    assert view_data is not None
    assert view_data["dispersion_pct"] == pytest.approx(60.0)


def test_criterio_3_serie_com_uma_barra():
    """A série do ativo com 1 barra usa previousClose; sem ele, o ativo é ignorado."""
    # Com previousClose no meta:
    prev = fechamento_anterior([10.50], 10.50, meta={"previousClose": 10.00})
    assert prev == 10.00

    # Com regularMarketPreviousClose no meta:
    prev_reg = fechamento_anterior(
        [10.50], 10.50, meta={"regularMarketPreviousClose": 10.00}
    )
    assert prev_reg == 10.00

    # Sem previousClose nem série suficiente:
    prev_nulo = fechamento_anterior([10.50], 10.50, meta={})
    assert prev_nulo is None


def test_criterio_4_duble_yahoo_falso_range():
    """O dublê com range=15d devolve 15 barras e chartPreviousClose igual ao fechamento
    anterior à primeira; com range=1d devolve exatamente o que devolve hoje.
    """
    res_15d = _resultado("PETR4.SA", "15d", "1d", tem_range=True)
    closes_15d = res_15d["indicators"]["quote"][0]["close"]
    assert len(closes_15d) == 15

    serie_esperada = _fechamentos("PETR4.SA", 15)
    anterior_esperado = serie_esperada[0]
    assert res_15d["meta"]["chartPreviousClose"] == anterior_esperado
    assert res_15d["meta"]["previousClose"] == closes_15d[-2]
    # chartPreviousClose é diferente do penúltimo fechamento quando a série varia
    assert res_15d["meta"]["chartPreviousClose"] != res_15d["meta"]["previousClose"]

    res_1d = _resultado("PETR4.SA", "1d", "1d", tem_range=True)
    closes_1d = res_1d["indicators"]["quote"][0]["close"]
    assert len(closes_1d) == 1
    # Com 1d, chartPreviousClose é o fechamento de ontem
    assert res_1d["meta"]["chartPreviousClose"] == _fechamentos("PETR4.SA", 1)[0]


def test_criterio_5_fronteira_chart_previous_close():
    """O teste de fronteira passa na codebase e falha no coletor com range=15d."""
    test_fronteira_chart_previous_close_coletores_reais()
    test_fronteira_chart_previous_close_falha_em_coletor_invalido()


@respx.mock
def test_criterio_6_quarentena_tres_acoes_ranking_e_em_revisao(monkeypatch):
    """Três ações com variação do dia +2%, −1% e +21% (a de +21% com chartPreviousClose irrelevante, já ignorado):
    o ranking do dia mostra as duas primeiras e a terceira só em 'Em revisão', com o +21% bruto e a fonte.
    """
    monkeypatch.setattr(
        "app.collectors.highlights.TICKERS", ["ACAO1", "ACAO2", "ACAO3"]
    )
    monkeypatch.setattr("app.collectors.utils.time.sleep", lambda s: None)
    monkeypatch.setattr(
        "app.collectors.highlights.consultar_segunda_fonte",
        lambda *args, **kwargs: None,
    )

    results = [
        criar_item_spark("ACAO1", [100.0, 102.0], preco=102.0, chart_prev=80.0),  # +2%
        criar_item_spark("ACAO2", [100.0, 99.0], preco=99.0, chart_prev=80.0),  # -1%
        criar_item_spark(
            "ACAO3", [100.0, 121.0], preco=121.0, chart_prev=80.0
        ),  # +21% (outlier)
    ]
    respx.get(url__regex=SPARK).respond(200, json={"spark": {"result": results}})

    data = fetch_yfinance()
    assert data is not None

    highs = json.loads(data.highs_json)
    lows = json.loads(data.lows_json)
    em_revisao = json.loads(data.em_revisao_json)

    # Ranking contém ACAO1 (+2%) e ACAO2 (-1%)
    assert any(h["ticker"] == "ACAO1" for h in highs)
    assert any(low["ticker"] == "ACAO2" for low in lows)
    assert not any(h["ticker"] == "ACAO3" for h in highs)
    assert not any(low["ticker"] == "ACAO3" for low in lows)

    # ACAO3 está apenas em "Em revisão"
    assert len(em_revisao) == 1
    r = em_revisao[0]
    assert r["ticker"] == "ACAO3"
    assert r["change_percent"] == pytest.approx(21.00)
    assert r["fonte"] == "yfinance"
    assert r["base"] == 100.0
    assert r["price"] == 121.0


@respx.mock
def test_criterio_7_outlier_confirmado_volta_ao_ranking(monkeypatch):
    """A mesma ação de +21% confirmada pela segunda fonte em +20,7% volta ao ranking."""
    monkeypatch.setattr("app.collectors.highlights.TICKERS", ["ACAO3"])
    monkeypatch.setattr("app.collectors.utils.time.sleep", lambda s: None)
    monkeypatch.setattr(
        "app.collectors.highlights.consultar_segunda_fonte",
        lambda symbol, price, fonte: 20.7,
    )

    results = [
        criar_item_spark("ACAO3", [100.0, 121.0], preco=121.0, chart_prev=80.0),  # +21%
    ]
    respx.get(url__regex=SPARK).respond(200, json={"spark": {"result": results}})

    data = fetch_yfinance()
    assert data is not None

    highs = json.loads(data.highs_json)
    em_revisao = json.loads(data.em_revisao_json)

    assert any(h["ticker"] == "ACAO3" for h in highs)
    assert not any(r["ticker"] == "ACAO3" for r in em_revisao)
    acao3 = [h for h in highs if h["ticker"] == "ACAO3"][0]
    assert "yfinance" in acao3["fonte"] and "mt5" in acao3["fonte"]


@respx.mock
def test_criterio_8_outlier_divergente_permanece_em_revisao(monkeypatch):
    """Ação de +21% cuja segunda fonte responde +4% permanece em 'Em revisão' e não aparece entre as cinco do dia."""
    monkeypatch.setattr("app.collectors.highlights.TICKERS", ["ACAO3"])
    monkeypatch.setattr("app.collectors.utils.time.sleep", lambda s: None)
    monkeypatch.setattr(
        "app.collectors.highlights.consultar_segunda_fonte",
        lambda symbol, price, fonte: 4.0,  # Divergência de 17 p.p. (> 0.5)
    )

    results = [
        criar_item_spark("ACAO3", [100.0, 121.0], preco=121.0, chart_prev=80.0),  # +21%
    ]
    respx.get(url__regex=SPARK).respond(200, json={"spark": {"result": results}})

    data = fetch_yfinance()
    assert data is not None

    highs = json.loads(data.highs_json)
    em_revisao = json.loads(data.em_revisao_json)

    assert not any(h["ticker"] == "ACAO3" for h in highs)
    assert any(r["ticker"] == "ACAO3" for r in em_revisao)


@respx.mock
def test_criterio_9_titulo_data_pregao_vs_relogio(monkeypatch):
    """Série cuja última barra é 2026-11-04: o título contém 04/11/2026 e não contém a data do relógio se ela for outra."""
    monkeypatch.setattr("app.collectors.highlights.TICKERS", ["PETR4"])
    monkeypatch.setattr("app.collectors.utils.time.sleep", lambda s: None)

    # Timestamp de 2026-11-04 18:00:00 BRT (UTC-3) -> 2026-11-04 21:00:00 UTC
    dt_alvo = datetime(2026, 11, 4, 21, 0, 0, tzinfo=timezone.utc)
    ts_alvo = int(dt_alvo.timestamp())

    item = criar_item_spark(
        "PETR4",
        [30.0, 31.0],
        preco=31.0,
        chart_prev=25.0,
        timestamps=[ts_alvo - 86400, ts_alvo],
    )
    respx.get(url__regex=SPARK).respond(200, json={"spark": {"result": [item]}})

    data = fetch_yfinance()
    assert data is not None
    assert data.pregao_data == "04/11/2026"

    save_highlights_data(data)
    view_data = get_highlights_view_data()
    assert view_data is not None
    assert "04/11/2026" in view_data["titulo_altas"]
    assert "04/11/2026" in view_data["titulo_baixas"]

    # Verifica renderização no HTML da página inicial
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Maiores altas · pregão 04/11/2026" in resp.text
    assert "Maiores baixas · pregão 04/11/2026" in resp.text


@respx.mock
def test_criterio_10_ticker_sem_base(monkeypatch):
    """Cesta com um ticker sem base: ele não altera up_count nem down_count, e o HTML diz que faltou dado para esse ticker."""
    monkeypatch.setattr(
        "app.collectors.highlights.TICKERS", ["PETR4", "VALE3", "SEMBASE"]
    )
    monkeypatch.setattr("app.collectors.utils.time.sleep", lambda s: None)

    results = [
        criar_item_spark(
            "PETR4", [30.0, 31.0], preco=31.0, chart_prev=25.0
        ),  # +3.33% (up)
        criar_item_spark(
            "VALE3", [60.0, 58.0], preco=58.0, chart_prev=50.0
        ),  # -3.33% (down)
        {
            "symbol": "SEMBASE.SA",
            "response": [
                {
                    "meta": {"regularMarketPrice": 10.0},
                    "timestamp": [],
                    "indicators": {"quote": [{"close": []}]},
                }
            ],
        },
    ]
    respx.get(url__regex=SPARK).respond(200, json={"spark": {"result": results}})

    data = fetch_yfinance()
    assert data is not None
    assert data.up_count == 1
    assert data.down_count == 1
    assert data.total_count == 2
    assert data.ausentes_count == 1
    assert "SEMBASE" in data.ausentes_json

    save_highlights_data(data)
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Faltou dado para SEMBASE" in resp.text


def test_invariante_api_snapshot():
    """Verifica campo em_revisao no painel altas_baixas em /api/snapshot."""
    resp = client.get("/api/snapshot")
    assert resp.status_code == 200
    dados = resp.json()
    altas_baixas = dados.get("paineis", {}).get("altas_baixas")
    if altas_baixas:
        assert "em_revisao" in altas_baixas
        assert isinstance(altas_baixas["em_revisao"], list)
