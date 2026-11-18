import json
from datetime import datetime, timezone
from app.database import save_historico_diario
from app.consultor import avaliador_historico
from app.database import get_connection


def setup_mock_data():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM snapshots_paineis WHERE painel = 'consultor_confianca'")
    conn.commit()
    conn.close()

    ibov_closes = [100000 + i for i in range(250)]
    ibov_volumes = [1000000 for _ in range(250)]
    # A série termina ontem: precisa caber na janela de 2 anos do backtest.
    hoje = datetime.now(timezone.utc).replace(
        hour=13, minute=0, second=0, microsecond=0
    )
    ibov_ts = [int(hoje.timestamp()) - (250 - i) * 86400 for i in range(250)]

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

    ticker_ts = ibov_ts.copy()

    # Queda lenta em zigue-zague (nunca duas quedas seguidas, para não cair na
    # R1) enquanto o Ibovespa sobe: a R2 dispara "Vender" na janela avaliada.
    ticker_closes = [100.0 - 0.2 * i + (0.3 if i % 2 else 0.0) for i in range(250)]

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

    from app.database import get_consultor_confianca

    regras = get_consultor_confianca()
    assert "R2 Tendência de baixa" in regras
    r2 = regras["R2 Tendência de baixa"]
    assert r2["disparos"] > 0
    assert 0 <= r2["acertos"] <= r2["disparos"]
    for campo in ("excesso_mediano", "janela_inicio", "janela_fim", "atualizado_em"):
        assert campo in r2
