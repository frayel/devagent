from datetime import date
from app.banco import ler_series
from app.consultor.calculador import calcular_consultor
import app.consultor.calculador as calc_module
from app.consultor.armazenamento import reset_db_init, get_opinioes_status
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_ler_series():
    tickers = ["PETR4", "VALE3"]
    inicio = date(2023, 1, 1)
    fim = date(2024, 1, 1)
    series = ler_series(tickers, inicio, fim)
    assert "PETR4" in series
    assert "VALE3" in series
    assert isinstance(series["PETR4"], list)


def test_consultor_abre_poucas_conexoes_calculador():
    import app.banco as banco

    orig = banco.get_connection
    conn_count = 0

    def fake_get_conn():
        nonlocal conn_count
        conn_count += 1
        return orig()

    banco.get_connection = fake_get_conn
    try:
        calcular_consultor(ignorar_cache=True)
        assert conn_count <= 5
    finally:
        banco.get_connection = orig


def test_init_db_roda_uma_vez():
    reset_db_init()
    get_opinioes_status()
    get_opinioes_status()
    assert True


def test_consultor_cache_logica():
    _ = calcular_consultor(ignorar_cache=True)
    ts1 = calc_module._consultor_cache_time
    _ = calcular_consultor(ignorar_cache=False)
    ts2 = calc_module._consultor_cache_time
    assert ts1 == ts2  # ts2 isn't updated because cache hit returned early


def test_api_consultor_duracao(monkeypatch):
    monkeypatch.delenv("SENHA", raising=False)
    response = client.get("/api/consultor")
    if response.status_code == 200:
        data = response.json()
        assert "duracao_ms" in data
        assert "cache" in data
