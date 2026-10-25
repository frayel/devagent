from fastapi.testclient import TestClient
from fastapi.routing import APIRoute
from datetime import date
from app.main import app
from app.banco import PREGOES_NO_SELETOR
import pytest

client = TestClient(app)


def test_regressao_nomes_de_parametro():
    rotas_com_data_str = []
    for route in app.routes:
        if isinstance(route, APIRoute):
            params = route.endpoint.__code__.co_varnames
            if "data_str" in params:
                if "data" not in params:
                    rotas_com_data_str.append(route.path)

    assert not rotas_com_data_str, (
        f"Rotas com data_str sem alias data: {rotas_com_data_str}"
    )


@pytest.fixture
def mock_snapshots(monkeypatch):
    def mock_listar_datas(*args, **kwargs):
        return [
            "2026-10-22",
            "2026-10-21",
            "2026-10-20",
            "2026-10-19",
            "2026-10-16",
            "2026-10-15",
            "2026-10-14",
        ]

    monkeypatch.setattr("app.banco.listar_datas", mock_listar_datas)

    def mock_obter_pregoes(agora, mercado_aberto, pregao_corr):
        pregoes = []
        if mercado_aberto:
            pregoes.append(str(pregao_corr))

        for d in mock_listar_datas():
            if d not in pregoes:
                pregoes.append(d)
            if len(pregoes) >= PREGOES_NO_SELETOR + 1:
                break
        return pregoes[: PREGOES_NO_SELETOR + 1]

    monkeypatch.setattr("app.main.obter_pregoes_disponiveis", mock_obter_pregoes)

    class DummyMercado:
        def mercado_aberto(self, dt):
            return False

        def pregao_corrente(self, dt):
            return date(2026, 10, 22)

        def ultimo_pregao_fechado(self, dt):
            return date(2026, 10, 22)

    monkeypatch.setattr("app.main.calendario", DummyMercado())
    return mock_listar_datas()


def test_get_index_seletor(mock_snapshots):
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.text

    assert '<select class="seletor-data"' in html
    assert 'name="data"' in html
    assert '<form method="get"' in html
    assert 'onchange="this.form.submit()"' in html
    assert "hx-get=" not in html.split('<select class="seletor-data"')[1].split(">")[0]

    # 6 options
    assert html.count('<option value="2026-10-') == 6
    assert 'value="2026-10-14"' not in html


def test_get_index_with_data(mock_snapshots):
    resp = client.get("/?data=2026-10-21")
    assert resp.status_code == 200
    assert 'value="2026-10-21" selected' in resp.text
    assert "Você está vendo o fechamento de 21/10/2026" in resp.text


def test_get_index_with_data_str(mock_snapshots):
    resp = client.get("/?data_str=2026-10-21")
    assert resp.status_code == 200
    assert 'value="2026-10-21" selected' in resp.text


def test_api_snapshot_404(mock_snapshots):
    resp = client.get("/api/snapshot?data=2099-01-01")
    assert resp.status_code == 404
    assert resp.json() == {"erro": "Data inválida ou fora da janela."}

    resp = client.get("/api/snapshot?data=2026-10-14")
    assert resp.status_code == 404


def test_api_snapshot_valid(mock_snapshots):
    resp = client.get("/api/snapshot?data=2026-10-21")
    assert resp.status_code == 200
