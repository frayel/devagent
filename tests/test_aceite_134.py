from datetime import datetime, timezone, timedelta
import json
import pytest
import respx
from fastapi.testclient import TestClient

from devagent.aceite import exigir_spec_done
from app.collectors.ibovespa import (
    LIMIAR_PCT_REVISAO,
    LIMIAR_PONTOS_REVISAO,
    fetch_yfinance,
)
from app.database import IbovespaData, save_ibovespa_data
from app.main import app
from app.services.ibovespa import get_ibovespa_view_data
from app.services.manchete import gerar_manchete

client = TestClient(app)
URL_YAHOO = (
    "https://query2.finance.yahoo.com/v8/finance/chart/^BVSP?range=1y&interval=1d"
)


@pytest.fixture(autouse=True)
def spec_134_done():
    exigir_spec_done("134")


@respx.mock
def test_criterio_1_duble_yahoo_250_fechamentos():
    """Dado um dublê do Yahoo com range=1y, 250 fechamentos, penúltimo 130000.0,

    último e preço atual 131300.0 e chartPreviousClose = 105000.0:
    fetch_yfinance().previous_close == 130000.0 e a variação calculada é +1,00%.
    """
    timestamps = [1700000000 + i * 86400 for i in range(250)]
    closes = [120000.0 + i * 10 for i in range(248)] + [130000.0, 131300.0]

    payload = {
        "chart": {
            "result": [
                {
                    "meta": {
                        "regularMarketPrice": 131300.0,
                        "chartPreviousClose": 105000.0,
                    },
                    "timestamp": timestamps,
                    "indicators": {"quote": [{"close": closes}]},
                }
            ]
        }
    }
    respx.get(URL_YAHOO).respond(200, json=payload)

    data = fetch_yfinance()
    assert data is not None
    assert data.previous_close == 130000.0
    assert data.current_price == 131300.0

    var_pct = ((data.current_price - data.previous_close) / data.previous_close) * 100
    assert var_pct == pytest.approx(1.0)


@respx.mock
def test_criterio_2_mt5_bloco_yahoo(monkeypatch):
    """O mesmo cenário montado com mt5: chartPreviousClose do MT5 é ignorado

    e previous_close vem da série.
    """
    from app.collectors import mt5, utils

    monkeypatch.setenv("MT5_API_URL", "http://mt5.teste:8000/api/v1/")
    monkeypatch.setenv("MT5_API_KEY", "chave-teste")
    monkeypatch.setattr(utils, "MIN_DELAY", 0.0)

    # 250 dias terminando em 2026-10-05
    fim = datetime(2026, 10, 5)
    dias = []
    d = fim
    while len(dias) < 250:
        if d.weekday() < 5:
            dias.append(d)
        d -= timedelta(days=1)
    dias.reverse()

    barras = []
    for i, dia in enumerate(dias):
        c = 120000.0 + i * 10
        if i == 248:
            c = 130000.0
        elif i == 249:
            c = 131300.0
        barras.append(
            {
                "time": dia.isoformat(),
                "open": c - 100,
                "high": c + 100,
                "low": c - 200,
                "close": c,
                "tick_volume": 10,
                "spread": 1,
                "real_volume": 1000,
            }
        )

    respx.get("http://mt5.teste:8000/api/v1/rates/from-pos").respond(
        200, json={"data": barras, "count": len(barras)}
    )

    bloco = mt5.bloco_yahoo("^BVSP", "1d", "1y")
    assert "chartPreviousClose" in bloco["meta"]

    # Quando fetch_yfinance roda com mt5 interceptando:
    data = fetch_yfinance()
    assert data is not None
    assert data.previous_close == 130000.0
    assert data.current_price == 131300.0


@respx.mock
def test_criterio_3_serie_anterior_a_hoje_com_preco_atual_diferente():
    """Série cuja última data é anterior a hoje e cujo preço atual difere

    do último fechamento: previous_close é o último fechamento.
    """
    # Datas de 2025 (claramente anteriores a hoje)
    payload = {
        "chart": {
            "result": [
                {
                    "meta": {
                        "regularMarketPrice": 132000.0,
                        "chartPreviousClose": 100000.0,
                    },
                    "timestamp": [1735689600, 1735776000],  # 2025-01-01, 2025-01-02
                    "indicators": {
                        "quote": [{"close": [128000.0, 130000.0]}]  # último é 130000
                    },
                }
            ]
        }
    }
    respx.get(URL_YAHOO).respond(200, json=payload)

    data = fetch_yfinance()
    assert data is not None
    assert data.previous_close == 130000.0


@respx.mock
def test_criterio_4_serie_com_1_fechamento_fallback(caplog):
    """Série com 1 fechamento e previousClose ausente: usa regularMarketPreviousClose.

    Sem ele, usa o preço atual e registra aviso no log.
    """
    # Caso 1: usa regularMarketPreviousClose
    payload_1 = {
        "chart": {
            "result": [
                {
                    "meta": {
                        "regularMarketPrice": 130000.0,
                        "regularMarketPreviousClose": 128500.0,
                    },
                    "timestamp": [1735689600],
                    "indicators": {"quote": [{"close": [130000.0]}]},
                }
            ]
        }
    }
    respx.get(URL_YAHOO).respond(200, json=payload_1)
    data1 = fetch_yfinance()
    assert data1 is not None
    assert data1.previous_close == 128500.0

    # Caso 2: sem regularMarketPreviousClose nem previousClose -> usa current_price e avisa
    respx.clear()
    payload_2 = {
        "chart": {
            "result": [
                {
                    "meta": {
                        "regularMarketPrice": 130000.0,
                    },
                    "timestamp": [1735689600],
                    "indicators": {"quote": [{"close": [130000.0]}]},
                }
            ]
        }
    }
    respx.get(URL_YAHOO).respond(200, json=payload_2)
    with caplog.at_level("WARNING"):
        data2 = fetch_yfinance()
    assert data2 is not None
    assert data2.previous_close == 130000.0
    assert any("previous_close ausente" in r.message for r in caplog.records)


def test_criterio_5_card_e_snapshot_com_dados_criterio_1():
    """Com o dado gravado pelo cenário do primeiro critério, GET / mostra +1,00%

    no card e GET /api/snapshot traz paineis.ibovespa.variacao_pct ≈ 1.0 e
    fechamento_anterior == 130000.0.
    """
    data = IbovespaData(
        timestamp=datetime.now(timezone.utc),
        current_price=131300.0,
        previous_close=130000.0,
        history_json=json.dumps({"dates": ["2026-11-08"], "closes": [130000.0]}),
        fonte="yfinance",
    )
    save_ibovespa_data(data)

    resp_card = client.get("/")
    assert resp_card.status_code == 200
    assert "+1,00%" in resp_card.text

    resp_snap = client.get("/api/snapshot")
    assert resp_snap.status_code == 200
    snap = resp_snap.json()
    ibov = snap["paineis"]["ibovespa"]
    assert ibov["fechamento_anterior"] == 130000.0
    assert ibov["variacao_pct"] == pytest.approx(1.0)


def test_criterio_6_queda_e_manchete():
    """Com o penúltimo fechamento acima do atual (queda de -0,80%), o card mostra

    -0,80%, is_positive é falso e a manchete de gerar_manchete diz 'baixa'.
    """
    # 130000 * (1 - 0.008) = 128960
    data = IbovespaData(
        timestamp=datetime.now(timezone.utc),
        current_price=128960.0,
        previous_close=130000.0,
        history_json=json.dumps({"dates": ["2026-11-08"], "closes": [130000.0]}),
        fonte="yfinance",
    )
    save_ibovespa_data(data)

    resp = client.get("/")
    assert resp.status_code == 200
    assert "-0,80%" in resp.text

    view_data = get_ibovespa_view_data()
    assert view_data is not None
    assert view_data["is_positive"] is False

    manchete = gerar_manchete(
        view_data,
        {"dispersion_pct": 30.0},
        {"estado": "Neutro"},
    )
    assert "baixa" in manchete.lower()


def test_criterio_7_limiares_de_revisao():
    """Valida limiares de sinal de revisão:

    - 131300 / 130000 (1% / 1300 pts) -> revisao_variacao falso
    - 167627 / 150704 (11,23% / 16923 pts) -> revisao_variacao verdadeiro, selo no HTML e ambos números
    - 5000 pts com 2% -> verdadeiro
    - 3.0% com 100 pts -> falso (corte estrito > 3.0)
    """
    assert LIMIAR_PCT_REVISAO == 3.0
    assert LIMIAR_PONTOS_REVISAO == 5000.0

    # 1. 131300 / 130000: falso
    d1 = IbovespaData(
        timestamp=datetime.now(timezone.utc),
        current_price=131300.0,
        previous_close=130000.0,
        history_json=json.dumps({"dates": [], "closes": []}),
    )
    save_ibovespa_data(d1)
    snap1 = client.get("/api/snapshot").json()["paineis"]["ibovespa"]
    assert snap1["revisao_variacao"] is False

    # 2. 167627 / 150704: verdadeiro
    d2 = IbovespaData(
        timestamp=datetime.now(timezone.utc),
        current_price=167627.0,
        previous_close=150704.0,
        history_json=json.dumps({"dates": [], "closes": []}),
    )
    save_ibovespa_data(d2)
    snap2 = client.get("/api/snapshot").json()["paineis"]["ibovespa"]
    assert snap2["revisao_variacao"] is True

    # Card HTML contém selo de revisão e ambos os números
    resp2 = client.get("/")
    assert resp2.status_code == 200
    assert "selo-revisao" in resp2.text or "em revisão" in resp2.text
    assert "16.923" in resp2.text
    assert "11,23%" in resp2.text

    # 3. |pontos| = 5000 com percentual de 2%: verdadeiro
    d3 = IbovespaData(
        timestamp=datetime.now(timezone.utc),
        current_price=255000.0,
        previous_close=250000.0,
        history_json=json.dumps({"dates": [], "closes": []}),
    )
    save_ibovespa_data(d3)
    snap3 = client.get("/api/snapshot").json()["paineis"]["ibovespa"]
    assert snap3["revisao_variacao"] is True

    # 4. Percentual de 3.0% com 100 pontos: falso (|pct| > 3.0 estrito)
    # 3333.3333333333335 * 1.03 = 3433.3333333333335 (variação = 100.0 pts, 3.0%)
    prev = 100.0 / 0.03
    curr = prev + 100.0
    d4 = IbovespaData(
        timestamp=datetime.now(timezone.utc),
        current_price=curr,
        previous_close=prev,
        history_json=json.dumps({"dates": [], "closes": []}),
    )
    save_ibovespa_data(d4)
    snap4 = client.get("/api/snapshot").json()["paineis"]["ibovespa"]
    assert snap4["revisao_variacao"] is False


def test_criterio_8_previous_close_ausente():
    """previous_close ausente: a página não contém 0,00% no card do Ibovespa

    e o snapshot traz a variação nula, com estado indisponível.
    """
    data = IbovespaData(
        timestamp=datetime.now(timezone.utc),
        current_price=131000.0,
        previous_close=0.0,
        history_json=json.dumps({"dates": [], "closes": []}),
        fonte="yfinance",
    )
    save_ibovespa_data(data)

    resp_card = client.get("/")
    assert resp_card.status_code == 200
    assert "0,00%" not in resp_card.text
    assert "131.000 pontos" in resp_card.text

    resp_snap = client.get("/api/snapshot")
    assert resp_snap.status_code == 200
    ibov = resp_snap.json()["paineis"]["ibovespa"]
    assert ibov["variacao_pct"] is None
    assert ibov["fechamento_anterior"] is None
    assert ibov["estado"] == "indisponivel"


def test_criterio_9_carimbo_pregao_anterior():
    """Carimbo 2026-11-04T18:10:00Z lido num instante de 05/11:

    o rodapé mostra 04/11/2026 15:10 BRT e o texto do card não chama esse número de hoje.
    """
    ts = datetime(2026, 11, 4, 18, 10, 0, tzinfo=timezone.utc)
    data = IbovespaData(
        timestamp=ts,
        current_price=167627.0,
        previous_close=150704.0,
        history_json=json.dumps({"dates": [], "closes": []}),
        fonte="yfinance",
    )
    save_ibovespa_data(data)

    # Simula leitura em 05/11
    instante_05 = datetime(2026, 11, 5, 12, 0, 0, tzinfo=timezone.utc)
    view_data = get_ibovespa_view_data(agora=instante_05)
    assert view_data is not None
    assert "04/11/2026 15:10 BRT" in view_data["time"]
    assert "hoje" not in view_data["titulo"].lower()
    assert view_data["titulo"] == "Ibovespa"
