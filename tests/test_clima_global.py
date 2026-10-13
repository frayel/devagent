import pytest
import respx
import re
from app.collectors import clima_global
from app.database import get_latest_clima_global_data


def make_chart_response(prev_close, close_price):
    return {
        "chart": {
            "result": [
                {
                    "meta": {
                        "chartPreviousClose": prev_close,
                        "regularMarketPrice": close_price,
                    },
                    "indicators": {"quote": [{"close": [close_price]}]},
                }
            ]
        }
    }


@respx.mock
def test_clima_global_aversao_a_risco(setup_db):
    respx.get(
        re.compile(r"https://query[12]\.finance\.yahoo\.com/v8/finance/chart/ES=F.*")
    ).respond(
        json=make_chart_response(100, 99)  # -1.0%
    )
    respx.get(
        re.compile(r"https://query[12]\.finance\.yahoo\.com/v8/finance/chart/\^VIX.*")
    ).respond(
        json=make_chart_response(10, 10.4)  # +4.0%
    )

    assert clima_global.collect_and_save() is True
    data = get_latest_clima_global_data()
    assert data is not None
    assert data.status == "Aversão a Risco"
    assert data.sp500_pct == -1.0
    assert data.vix_pct == pytest.approx(4.0)


@respx.mock
def test_clima_global_apetite_a_risco(setup_db):
    respx.get(
        re.compile(r"https://query[12]\.finance\.yahoo\.com/v8/finance/chart/ES=F.*")
    ).respond(
        json=make_chart_response(100, 101)  # +1.0%
    )
    respx.get(
        re.compile(r"https://query[12]\.finance\.yahoo\.com/v8/finance/chart/\^VIX.*")
    ).respond(
        json=make_chart_response(10, 9.7)  # -3.0%
    )

    assert clima_global.collect_and_save() is True
    data = get_latest_clima_global_data()
    assert data is not None
    assert data.status == "Apetite a Risco"
    assert data.sp500_pct == 1.0
    assert data.vix_pct == pytest.approx(-3.0)


@respx.mock
def test_clima_global_neutro(setup_db):
    respx.get(
        re.compile(r"https://query[12]\.finance\.yahoo\.com/v8/finance/chart/ES=F.*")
    ).respond(
        json=make_chart_response(100, 100.2)  # +0.2%
    )
    respx.get(
        re.compile(r"https://query[12]\.finance\.yahoo\.com/v8/finance/chart/\^VIX.*")
    ).respond(
        json=make_chart_response(10, 10.1)  # +1.0%
    )

    assert clima_global.collect_and_save() is True
    data = get_latest_clima_global_data()
    assert data is not None
    assert data.status == "Neutro"
    assert data.sp500_pct == pytest.approx(0.2)
    assert data.vix_pct == pytest.approx(1.0)
