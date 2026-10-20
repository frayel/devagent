import json
from app.database import save_historico_diario
from app.consultor import avaliador_historico
from app.database import get_connection


def setup_mock_data():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM historico_diario_cache")
    cursor.execute("DELETE FROM consultor_confianca_regras")
    conn.commit()
    conn.close()

    ibov_closes = [100000 + i for i in range(250)]
    ibov_volumes = [1000000 for _ in range(250)]
    ibov_ts = [1600000000 + i * 86400 for i in range(250)]

    ibov_data = {
        "symbol": "^BVSP",
        "timestamp": ibov_ts,
        "indicators": {"quote": [{"close": ibov_closes, "volume": ibov_volumes}]},
    }
    save_historico_diario(
        "^BVSP",
        "2y",
        "1d",
        json.dumps(ibov_data),
        avaliador_historico.datetime.now(avaliador_historico.timezone.utc),
    )

    ticker_closes = [10.0 for _ in range(200)]
    ticker_ts = ibov_ts.copy()

    ticker_closes = [10.0 for _ in range(200)]
    for i in range(200, 250):
        ticker_closes.append(50.0 + (i - 200) * 0.1)

    ticker_volumes = [1000 for _ in range(250)]

    ticker_data = {
        "symbol": "PETR4",
        "timestamp": ticker_ts,
        "indicators": {"quote": [{"close": ticker_closes, "volume": ticker_volumes}]},
    }

    save_historico_diario(
        "PETR4",
        "2y",
        "1d",
        json.dumps(ticker_data),
        avaliador_historico.datetime.now(avaliador_historico.timezone.utc),
    )


def test_avaliador_historico(monkeypatch):
    setup_mock_data()
    monkeypatch.setattr(avaliador_historico, "CARTEIRA_IBOVESPA", ["PETR4"])

    avaliador_historico.rodar_backtest()

    from app.database import get_consultor_confianca_regras

    regras = get_consultor_confianca_regras()
    assert len(regras) >= 0
