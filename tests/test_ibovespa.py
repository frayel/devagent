import json

import respx
from fastapi.testclient import TestClient

from app.collectors.ibovespa import (
    collect_and_save,
    fetch_yfinance,
    calc_mm,
)
from app.database import get_latest_ibovespa_data
from app.main import app

import subprocess

client = TestClient(app)


def test_data_db_not_in_git():
    # Run git ls-files to ensure data.db is not tracked
    result = subprocess.run(
        ["git", "ls-files", "data.db"], capture_output=True, text=True, check=True
    )
    assert result.stdout.strip() == "", "data.db should not be tracked by git"


def load_fixture(name):
    with open(f"tests/fixtures/{name}") as f:
        return json.load(f)


def test_calculate_moving_averages():
    closes = [10.0, 20.0, 30.0, 40.0, 50.0]

    # Not enough data for moving average of 10
    assert calc_mm(closes, 10) is None

    # Moving average of 3
    # last 3 are 30.0, 40.0, 50.0
    assert calc_mm(closes, 3) == 40.0

    # Moving average of 5
    assert calc_mm(closes, 5) == 30.0


@respx.mock
def test_fetch_yfinance_success():
    yfinance_data = load_fixture("yfinance_response.json")
    respx.get(
        "https://query2.finance.yahoo.com/v8/finance/chart/^BVSP?range=1y&interval=1d"
    ).respond(status_code=200, json=yfinance_data)
    data = fetch_yfinance()
    assert data is not None
    assert data.current_price == 131000.0
    assert data.previous_close == 132000.0
    assert data.fonte == "yfinance"

    history_json = json.loads(data.history_json)
    assert len(history_json["dates"]) <= 30
    assert len(history_json["closes"]) <= 30


@respx.mock
def test_collect_and_save_pelo_yahoo():
    yfinance_data = load_fixture("yfinance_response.json")
    respx.get(
        "https://query2.finance.yahoo.com/v8/finance/chart/^BVSP?range=1y&interval=1d"
    ).respond(status_code=200, json=yfinance_data)

    assert collect_and_save() is True

    db_data = get_latest_ibovespa_data()
    assert db_data is not None
    assert db_data.current_price == 131000.0
    assert db_data.previous_close == 132000.0
    assert db_data.fonte == "yfinance"


@respx.mock
def test_index_route():
    # Test when DB has no data
    response = client.get("/")
    assert response.status_code == 200
    assert "Dado indisponível agora" in response.text

    # Add data to DB
    respx.get(
        "https://query2.finance.yahoo.com/v8/finance/chart/^BVSP?range=1y&interval=1d"
    ).respond(status_code=200, json=load_fixture("yfinance_response.json"))
    collect_and_save()

    response = client.get("/")
    assert response.status_code == 200
    assert "131.000" in response.text
    assert "Fonte yfinance" in response.text


@respx.mock
def test_fechamento_anterior_ignora_chart_previous_close_antigo():
    """Regressão #787: chartPreviousClose de 1 ano atrás (>20% de variação) não pode

    ser usado como previous_close, pois descartava o dado e congelava o gráfico.
    """
    payload = {
        "chart": {
            "result": [
                {
                    "meta": {
                        "regularMarketPrice": 168498.45,
                        # Fechamento de 1 ano atrás: se usado, variação é ~40% (> 20%)
                        "chartPreviousClose": 120000.0,
                    },
                    "timestamp": [1793883600, 1793970000],
                    "indicators": {
                        "quote": [
                            {
                                "close": [166192.0, 168499.0],
                            }
                        ]
                    },
                }
            ]
        }
    }
    respx.get(
        "https://query2.finance.yahoo.com/v8/finance/chart/^BVSP?range=1y&interval=1d"
    ).respond(status_code=200, json=payload)

    data = fetch_yfinance()
    assert data is not None, "Coleta não deve ser descartada por variação implausível"
    assert data.current_price == 168498.45
    # previous_close deve ser o do pregão anterior (166192.0), não o de 1 ano atrás (120000.0)
    assert data.previous_close == 166192.0

    history_json = json.loads(data.history_json)
    assert len(history_json["dates"]) == 2
    assert history_json["closes"][-1] == 168499.0


@respx.mock
def test_fechamento_anterior_antes_da_abertura():
    """Quando o último candle é de ontem e o preço atual difere (pré-abertura),

    o previous_close é o fechamento de ontem.
    """
    payload = {
        "chart": {
            "result": [
                {
                    "meta": {
                        "regularMarketPrice": 169000.0,
                        "chartPreviousClose": 120000.0,
                    },
                    "timestamp": [1793797200, 1793883600],
                    "indicators": {
                        "quote": [
                            {
                                "close": [165529.0, 167564.0],
                            }
                        ]
                    },
                }
            ]
        }
    }
    respx.get(
        "https://query2.finance.yahoo.com/v8/finance/chart/^BVSP?range=1y&interval=1d"
    ).respond(status_code=200, json=payload)

    data = fetch_yfinance()
    assert data is not None
    assert data.previous_close == 167564.0


@respx.mock
def test_collect_and_save_retry_on_transient_db_error(monkeypatch):
    """Regressão #793: collect_and_save deve tentar novamente se save_ibovespa_data

    falhar temporariamente por disjuntor/inicialização do banco.
    """
    import app.collectors.ibovespa as ibov_mod
    from app.banco import DBInacessivelError

    yfinance_data = load_fixture("yfinance_response.json")
    respx.get(
        "https://query2.finance.yahoo.com/v8/finance/chart/^BVSP?range=1y&interval=1d"
    ).respond(status_code=200, json=yfinance_data)

    tentativas = [0]
    orig_save = ibov_mod.save_ibovespa_data

    def mock_save(data):
        tentativas[0] += 1
        if tentativas[0] == 1:
            raise DBInacessivelError("Disjuntor aberto")
        return orig_save(data)

    monkeypatch.setattr(ibov_mod, "save_ibovespa_data", mock_save)
    monkeypatch.setattr(ibov_mod.time, "sleep", lambda s: None)

    assert ibov_mod.collect_and_save() is True
    assert tentativas[0] == 2
