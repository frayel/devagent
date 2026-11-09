import logging
import re
from pathlib import Path

import pytest
import respx
from fastapi.testclient import TestClient

from devagent.aceite import exigir_spec_done
from app.collectors import ibovespa, utils
from app.main import app
from tests.test_mt5 import rota_rates, BASE, CHAVE

client = TestClient(app)
URL_YAHOO = re.compile(
    r"https://query[12]\.finance\.yahoo\.com/v8/finance/chart/\^BVSP.*"
)


@pytest.fixture(autouse=True)
def spec_136_done():
    exigir_spec_done("136")


@pytest.fixture(autouse=True)
def sem_espera(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(utils, "MIN_DELAY", 0.0)
    monkeypatch.setattr(utils.time, "sleep", lambda s: None)


def chart_yahoo(fechamento_anterior: float, atual: float) -> dict:
    return {
        "chart": {
            "result": [
                {
                    "meta": {
                        "regularMarketPrice": atual,
                        "chartPreviousClose": fechamento_anterior,
                    },
                    "timestamp": [1761652800, 1761739200],
                    "indicators": {"quote": [{"close": [fechamento_anterior, atual]}]},
                }
            ]
        }
    }


def barras_mt5(fechamento_anterior: float, atual: float) -> list[dict]:
    return [
        {
            "time": "2026-10-04T18:00:00",
            "open": fechamento_anterior,
            "high": fechamento_anterior + 100,
            "low": fechamento_anterior - 100,
            "close": fechamento_anterior,
            "tick_volume": 100,
            "spread": 1,
            "real_volume": 1000,
        },
        {
            "time": "2026-10-05T18:00:00",
            "open": atual - 100,
            "high": atual + 100,
            "low": atual - 200,
            "close": atual,
            "tick_volume": 100,
            "spread": 1,
            "real_volume": 1000,
        },
    ]


@respx.mock
def test_criterio_1_mt5_e_yahoo_divergem(monkeypatch, caplog):
    """MT5 com +12,87% e Yahoo com −0,80% (divergem): nada é gravado, collect_and_save() devolve False e o log traz as duas variações."""
    monkeypatch.setenv("MT5_API_URL", BASE + "/")
    monkeypatch.setenv("MT5_API_KEY", CHAVE)

    # MT5: 100.000 -> 112.870 (+12.87%)
    rota_rates({"IBOV:D1": barras_mt5(100_000.0, 112_870.0)})

    # Yahoo: 100.000 -> 99.200 (-0.80%)
    respx.get(url__regex=URL_YAHOO).respond(200, json=chart_yahoo(100_000.0, 99_200.0))

    salvou = []
    monkeypatch.setattr(ibovespa, "save_ibovespa_data", lambda d: salvou.append(d))

    with caplog.at_level(logging.ERROR):
        sucesso = ibovespa.collect_and_save()

    assert sucesso is False
    assert len(salvou) == 0
    assert "+12.87%" in caplog.text or "12.87%" in caplog.text
    assert "-0.80%" in caplog.text or "0.80%" in caplog.text


@respx.mock
def test_criterio_2_mt5_e_yahoo_concordam(monkeypatch, caplog):
    """MT5 com +12,87% e Yahoo com +12,60%: grava a variação do MT5, com fonte = 'mt5', e registra o motivo de confirmação."""
    monkeypatch.setenv("MT5_API_URL", BASE + "/")
    monkeypatch.setenv("MT5_API_KEY", CHAVE)

    # MT5: 100.000 -> 112.870 (+12.87%)
    rota_rates({"IBOV:D1": barras_mt5(100_000.0, 112_870.0)})

    # Yahoo: 100.000 -> 112.600 (+12.60%)
    respx.get(url__regex=URL_YAHOO).respond(200, json=chart_yahoo(100_000.0, 112_600.0))

    salvou = []
    monkeypatch.setattr(ibovespa, "save_ibovespa_data", lambda d: salvou.append(d))

    with caplog.at_level(logging.INFO):
        sucesso = ibovespa.collect_and_save()

    assert sucesso is True
    assert len(salvou) == 1
    dado_salvo = salvou[0]
    assert dado_salvo.fonte == "mt5"
    assert dado_salvo.current_price == 112_870.0
    assert "confirmada por mt5 e yfinance" in caplog.text


@respx.mock
def test_criterio_3_mt5_desligado_yahoo_extremo(monkeypatch, caplog):
    """MT5 desligado, Yahoo com +12,87%: sem segunda fonte, collect_and_save() devolve False e não grava."""
    monkeypatch.delenv("MT5_API_URL", raising=False)

    # Yahoo: 100.000 -> 112.870 (+12.87%)
    respx.get(url__regex=URL_YAHOO).respond(200, json=chart_yahoo(100_000.0, 112_870.0))

    salvou = []
    monkeypatch.setattr(ibovespa, "save_ibovespa_data", lambda d: salvou.append(d))

    with caplog.at_level(logging.ERROR):
        sucesso = ibovespa.collect_and_save()

    assert sucesso is False
    assert len(salvou) == 0
    assert "sem segunda fonte" in caplog.text


@respx.mock
def test_criterio_4_mt5_extremo_yahoo_fora_do_ar(monkeypatch, caplog):
    """MT5 com +12,87% e Yahoo fora do ar (erro HTTP): não grava, motivo 'sem segunda fonte'."""
    monkeypatch.setenv("MT5_API_URL", BASE + "/")
    monkeypatch.setenv("MT5_API_KEY", CHAVE)

    # MT5: 100.000 -> 112.870 (+12.87%)
    rota_rates({"IBOV:D1": barras_mt5(100_000.0, 112_870.0)})

    # Yahoo fora do ar (500)
    respx.get(url__regex=URL_YAHOO).respond(500)

    salvou = []
    monkeypatch.setattr(ibovespa, "save_ibovespa_data", lambda d: salvou.append(d))

    with caplog.at_level(logging.ERROR):
        sucesso = ibovespa.collect_and_save()

    assert sucesso is False
    assert len(salvou) == 0
    assert "sem segunda fonte" in caplog.text


@respx.mock
def test_criterio_5_variacao_normal_sem_chamada_extra(monkeypatch):
    """Variação de +3,00%: nenhuma chamada extra (espião no cliente HTTP prova que só a fonte principal foi chamada)."""
    monkeypatch.setenv("MT5_API_URL", BASE + "/")
    monkeypatch.setenv("MT5_API_KEY", CHAVE)

    # MT5: 100.000 -> 103.000 (+3.00%)
    rota_rates({"IBOV:D1": barras_mt5(100_000.0, 103_000.0)})

    yahoo_rota = respx.get(url__regex=URL_YAHOO).respond(
        200, json=chart_yahoo(100_000.0, 103_000.0)
    )

    salvou = []
    monkeypatch.setattr(ibovespa, "save_ibovespa_data", lambda d: salvou.append(d))

    sucesso = ibovespa.collect_and_save()

    assert sucesso is True
    assert len(salvou) == 1
    # Yahoo NÃO foi chamado pois variação <= 10%
    assert not yahoo_rota.called


@respx.mock
def test_criterio_6_variacao_acima_de_20_descartada_mesmo_com_concordancia(monkeypatch):
    """Variação de +25% com as duas fontes concordando: descartada."""
    monkeypatch.setenv("MT5_API_URL", BASE + "/")
    monkeypatch.setenv("MT5_API_KEY", CHAVE)

    # MT5: 100.000 -> 125.000 (+25.00%)
    rota_rates({"IBOV:D1": barras_mt5(100_000.0, 125_000.0)})

    # Yahoo: 100.000 -> 125.000 (+25.00%)
    respx.get(url__regex=URL_YAHOO).respond(200, json=chart_yahoo(100_000.0, 125_000.0))

    salvou = []
    monkeypatch.setattr(ibovespa, "save_ibovespa_data", lambda d: salvou.append(d))

    sucesso = ibovespa.collect_and_save()
    assert sucesso is False
    assert len(salvou) == 0


def test_criterio_7_todas_ocorrencias_15_99_tem_relatado():
    """Nenhuma ocorrência de '15,99%' em app/, auditoria/ e CHANGELOG.md afirma o fato sem a ressalva 'relatado'."""
    raiz = Path(".")
    pastas_e_arquivos = [raiz / "app", raiz / "auditoria", raiz / "CHANGELOG.md"]

    arquivos = []
    for item in pastas_e_arquivos:
        if item.is_file():
            arquivos.append(item)
        elif item.is_dir():
            for p in item.rglob("*"):
                if p.is_file() and p.suffix in (".py", ".md", ".txt"):
                    arquivos.append(p)

    erros = []
    for arq in arquivos:
        linhas = arq.read_text(encoding="utf-8").splitlines()
        for idx, linha in enumerate(linhas, 1):
            if "15,99" in linha or "15.99%" in linha:
                if "relatado" not in linha.lower():
                    erros.append(f"{arq}:{idx}: {linha}")

    assert not erros, "Ocorrências de 15,99% sem 'relatado':\n" + "\n".join(erros)
