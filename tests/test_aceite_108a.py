from datetime import date, timedelta
from app.banco import init_db, gravar_serie
from app.database import get_historico_diario
import os


def test_get_historico_diario_timestamps_and_coletado_em():
    os.environ["BANCO_TIPO"] = "sqlite"
    init_db()
    hoje = date.today()
    barras = [
        {
            "data": (hoje - timedelta(days=2)).isoformat(),
            "open": 100,
            "high": 105,
            "low": 95,
            "close": 101,
            "volume": 1000,
        },
        {
            "data": (hoje - timedelta(days=1)).isoformat(),
            "open": 101,
            "high": 106,
            "low": 96,
            "close": 102,
            "volume": 1100,
        },
        {
            "data": hoje.isoformat(),
            "open": 102,
            "high": 107,
            "low": 97,
            "close": 103,
            "volume": 1200,
        },
    ]
    gravar_serie("MOCK3", barras)

    res = get_historico_diario(["MOCK3"], "3d", "1d")
    timestamps = res["MOCK3"]["timestamp"]
    assert 1 not in timestamps
    assert timestamps[0] < timestamps[1] < timestamps[2]
    assert "metadata" in res["MOCK3"]
    assert "criado_em" in res["MOCK3"]["metadata"]
