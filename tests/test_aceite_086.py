from datetime import date
from fastapi.testclient import TestClient


def test_086_get_historico_diario(monkeypatch):
    from app.database import get_historico_diario
    from app.banco import init_db, gravar_serie

    import app.banco

    app.banco._db_initialized = False
    init_db()

    hoje = date.today()
    barras = [
        {
            "data": hoje.strftime("%Y-%m-%d"),
            "close": 10.0,
            "open": 9.0,
            "high": 11.0,
            "low": 8.0,
            "volume": 100,
        },
    ]
    gravar_serie("FIX086", barras)

    res = get_historico_diario(["FIX086"], "1mo", "1d")

    assert "FIX086" in res
    ts = res["FIX086"]["timestamp"]
    assert ts[0] != 1
    assert ts[0] > 0
    assert "criado_em" in res["FIX086"].get("metadata", {})


def test_086_consultor_sinais_atualizados(monkeypatch):
    from app.main import app

    client = TestClient(app)

    monkeypatch.delenv("SENHA", raising=False)

    response = client.get("/api/consultor")
    assert response.status_code == 200
    dados = response.json()
    assert "informacoes_de" in dados
    info = dados["informacoes_de"]
    assert "sinais_pregao" in info
    assert "sinais_coletado_em" in info
    assert "opinioes_extraidas_em" in info
    assert "composicao_conferida_em" in info
    assert "estado_sinais" in info
    assert "estado_opinioes" in info
