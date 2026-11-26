"""Barra diária defasada do MT5 não vira cotação do dia.

Em 26/11/2026, às 12:05 BRT, com o pregão aberto, o terminal MT5 devolvia
como última barra diária a de 25/11. O card do Ibovespa mostrou 166.685
(fechamento de 25/11) enquanto o índice estava em 173.450, e a auditoria
reprovou `ibov.confere_com_fonte` (diferença de 3,86%). Passada a folga depois
da abertura, a série diária que não chega ao pregão do dia é recusada e a
coleta segue para o Yahoo.
"""

from datetime import date, datetime, timedelta, timezone

import httpx
import pytest
import respx

from app.collectors import mt5, registro_fontes, utils
from app.collectors.utils import fetch_with_retry

BASE = "http://mt5.teste:8000/api/v1"
RATES = f"{BASE}/rates/from-pos"
BRT = timezone(timedelta(hours=-3))
URL_IBOV = (
    "https://query2.finance.yahoo.com/v8/finance/chart/%5EBVSP?range=1mo&interval=1d"
)


def em(dia: int, hora: int, minuto: int = 0, mes: int = 11) -> datetime:
    return datetime(2026, mes, dia, hora, minuto, tzinfo=BRT)


@pytest.fixture
def mt5_ligado(monkeypatch):
    monkeypatch.setenv("MT5_API_URL", BASE)
    monkeypatch.setenv("MT5_API_KEY", "chave")
    monkeypatch.setattr(utils, "MIN_DELAY", 0.0)
    monkeypatch.setattr(mt5, "CONFERIR_DEFASAGEM", True)


def relogio(monkeypatch, agora: datetime) -> None:
    monkeypatch.setattr(mt5, "_agora", lambda: agora)


def barras_ate(ultimo: date, n: int = 30) -> list[dict]:
    dias: list[date] = []
    d = ultimo
    while len(dias) < n:
        if d.weekday() < 5:
            dias.append(d)
        d -= timedelta(days=1)
    dias.reverse()
    return [
        {
            "time": datetime.combine(d, datetime.min.time()).isoformat(),
            "open": 160000.0 + i,
            "high": 160000.5 + i,
            "low": 159999.5 + i,
            "close": 160000.25 + i,
            "tick_volume": 10,
            "real_volume": 1000,
        }
        for i, d in enumerate(dias)
    ]


@pytest.mark.parametrize(
    "agora, esperado",
    [
        (em(26, 12, 5), date(2026, 11, 26)),  # pregão aberto
        (em(26, 10, 15), date(2026, 11, 26)),  # fim da folga
        (em(26, 10, 14), date(2026, 11, 25)),  # barra do dia ainda pode faltar
        (em(26, 8, 0), date(2026, 11, 25)),  # antes da abertura
        (em(26, 20, 0), date(2026, 11, 26)),  # depois do fechamento
        (em(28, 11, 0), date(2026, 11, 27)),  # sábado: sexta
        (em(23, 9, 0), date(2026, 11, 19)),  # segunda cedo, depois do feriado de 20/11
    ],
)
def test_pregao_esperado(agora, esperado):
    assert mt5.pregao_esperado(agora) == esperado


def test_defasagem_texto():
    assert mt5.defasagem(date(2026, 11, 26), em(26, 12, 5)) is None
    assert mt5.defasagem(date(2026, 11, 25), em(26, 12, 5)) == (
        "barra diária defasada (última 25/11/2026; pregão esperado 26/11/2026)"
    )


@respx.mock
def test_barra_de_ontem_com_pregao_aberto_vai_para_o_yahoo(mt5_ligado, monkeypatch):
    relogio(monkeypatch, em(26, 12, 5))
    rota = respx.get(RATES).mock(
        return_value=httpx.Response(200, json={"data": barras_ate(date(2026, 11, 25))})
    )
    yahoo = respx.get(url__regex=r"https://query[12]\.finance\.yahoo\.com.*").mock(
        return_value=httpx.Response(200, json={"chart": {"result": [], "error": None}})
    )

    resp = fetch_with_retry(URL_IBOV)

    assert rota.called
    assert yahoo.called
    assert resp.headers.get("X-Fonte") != "mt5"
    fonte = registro_fontes.fontes()[registro_fontes.MT5]
    assert "barra diária defasada" in (fonte.ultimo_erro or "")
    assert fonte.graves[-1] is False

    # O símbolo fica em pausa: a rodada seguinte não pede as barras de novo.
    mt5._cache.clear()
    fetch_with_retry(URL_IBOV)
    assert rota.call_count == 1


@respx.mock
def test_barra_do_dia_continua_no_mt5(mt5_ligado, monkeypatch):
    relogio(monkeypatch, em(26, 12, 5))
    respx.get(RATES).mock(
        return_value=httpx.Response(200, json={"data": barras_ate(date(2026, 11, 26))})
    )
    yahoo = respx.get(url__regex=r"https://query[12]\.finance\.yahoo\.com.*")

    resp = fetch_with_retry(URL_IBOV)

    assert not yahoo.called
    assert resp.headers["X-Fonte"] == "mt5"
    meta = resp.json()["chart"]["result"][0]["meta"]
    assert meta["regularMarketPrice"] == 160000.25 + 29


@respx.mock
def test_antes_da_folga_a_barra_de_ontem_vale(mt5_ligado, monkeypatch):
    relogio(monkeypatch, em(26, 9, 30))
    respx.get(RATES).mock(
        return_value=httpx.Response(200, json={"data": barras_ate(date(2026, 11, 25))})
    )
    yahoo = respx.get(url__regex=r"https://query[12]\.finance\.yahoo\.com.*")

    resp = fetch_with_retry(URL_IBOV)

    assert not yahoo.called
    assert resp.headers["X-Fonte"] == "mt5"


@respx.mock
def test_ibovespa_com_mt5_parado_grava_o_valor_do_yahoo(mt5_ligado, monkeypatch):
    """Ponta a ponta no coletor: o card leva o valor do dia, não o de ontem."""
    from app.collectors import ibovespa
    from app.database import get_latest_ibovespa_data

    relogio(monkeypatch, em(26, 12, 5))
    respx.get(RATES).mock(
        return_value=httpx.Response(200, json={"data": barras_ate(date(2026, 11, 25))})
    )
    datas = [date(2026, 11, d) for d in (19, 23, 24, 25, 26)]
    fechamentos = [166376.0, 164796.0, 164090.0, 166685.0, 173450.1]
    corpo = {
        "chart": {
            "result": [
                {
                    "meta": {
                        "symbol": "^BVSP",
                        "regularMarketPrice": 173450.1,
                        "regularMarketTime": int(em(26, 11, 51).timestamp()),
                        "chartPreviousClose": 167538.0,
                        "previousClose": 166685.0,
                    },
                    "timestamp": [
                        int(
                            datetime(
                                d.year, d.month, d.day, 13, tzinfo=timezone.utc
                            ).timestamp()
                        )
                        for d in datas
                    ],
                    "indicators": {"quote": [{"close": fechamentos}]},
                }
            ],
            "error": None,
        }
    }
    respx.get(url__regex=r"https://query[12]\.finance\.yahoo\.com.*").mock(
        return_value=httpx.Response(200, json=corpo)
    )

    assert ibovespa.collect_and_save()
    dado = get_latest_ibovespa_data()
    assert dado is not None
    assert dado.current_price == pytest.approx(173450.1)
    assert dado.fonte != "mt5"
