import pytest
import respx
import httpx

from app.collectors import concentracao_setorial
from app.database import get_latest_concentracao_setorial_data


@pytest.fixture
def mock_brapi_response():
    return {
        "results": [
            {
                "symbol": "PETR4",
                "regularMarketPrice": 30.5,
                "regularMarketPreviousClose": 30.0,
                "regularMarketVolume": 1000,
            },
            {
                "symbol": "VALE3",
                "regularMarketPrice": 61.2,
                "regularMarketPreviousClose": 60.0,
                "regularMarketVolume": 2000,
            },
            {
                "symbol": "ITUB4",
                "regularMarketPrice": 25.0,
                "regularMarketPreviousClose": 24.5,
                "regularMarketVolume": 5000,
            },
        ]
    }


@pytest.fixture
def mock_yfinance_response():
    return {
        "spark": {
            "result": [
                {
                    "symbol": "PETR4.SA",
                    "response": [
                        {
                            "meta": {
                                "regularMarketPrice": 30.5,
                                "chartPreviousClose": 30.0,
                            }
                        }
                    ],
                },
                {
                    "symbol": "VALE3.SA",
                    "response": [
                        {
                            "meta": {
                                "regularMarketPrice": 61.2,
                                "chartPreviousClose": 60.0,
                            }
                        }
                    ],
                },
            ]
        }
    }


def test_coleta_concentracao_setorial_com_brapi(
    mock_brapi_response, monkeypatch, setup_db
):
    monkeypatch.setenv("BRAPI_TOKEN", "fake_token")

    with respx.mock:
        respx.get(url__startswith="https://brapi.dev").mock(
            return_value=httpx.Response(200, json=mock_brapi_response)
        )

        sucesso = concentracao_setorial.collect_and_save()
        assert sucesso is True

        data = get_latest_concentracao_setorial_data()
        assert data is not None
        assert data.fonte == "brapi"
        # VALE3 sobe 2,0%, PETR4 1,67%, ITUB4 2,04%: Financeiro lidera.
        assert data.setor_destaque == "Financeiro"
        assert data.variacao_media == pytest.approx(2.0408, abs=1e-3)


def test_coleta_concentracao_setorial_com_yfinance_fallback(
    mock_yfinance_response, monkeypatch, setup_db
):
    monkeypatch.delenv("BRAPI_TOKEN", raising=False)

    with respx.mock:
        respx.get(url__startswith="https://brapi.dev").mock(
            return_value=httpx.Response(500)
        )
        respx.get(url__startswith="https://query1.finance.yahoo.com").mock(
            return_value=httpx.Response(200, json=mock_yfinance_response)
        )

        sucesso = concentracao_setorial.collect_and_save()
        assert sucesso is True

        data = get_latest_concentracao_setorial_data()
        assert data is not None
        assert data.fonte == "yfinance"


def test_coleta_concentracao_setorial_falha_total(monkeypatch, setup_db):
    monkeypatch.delenv("BRAPI_TOKEN", raising=False)

    with respx.mock:
        respx.get(url__startswith="https://brapi.dev").mock(
            return_value=httpx.Response(500)
        )
        respx.get(url__startswith="https://query1.finance.yahoo.com").mock(
            return_value=httpx.Response(500)
        )

        sucesso = concentracao_setorial.collect_and_save()
        assert sucesso is False

        data = get_latest_concentracao_setorial_data()
        assert data is None


def _salvar(setor: str, variacao: float) -> None:
    from datetime import datetime, timezone

    from app.database import (
        ConcentracaoSetorialData,
        save_concentracao_setorial_data,
    )

    save_concentracao_setorial_data(
        ConcentracaoSetorialData(
            timestamp=datetime.now(timezone.utc),
            setor_destaque=setor,
            variacao_media=variacao,
            fonte="brapi",
        )
    )


def test_acao_fora_do_mapa_nao_vira_setor(monkeypatch, setup_db):
    """Um ticker sem setor conhecido não pode ser apontado como líder."""
    monkeypatch.setenv("BRAPI_TOKEN", "fake_token")
    resposta = {
        "results": [
            {
                "symbol": "XPTO3",
                "regularMarketPrice": 20.0,
                "regularMarketPreviousClose": 10.0,
            },
            {
                "symbol": "PETR4",
                "regularMarketPrice": 30.3,
                "regularMarketPreviousClose": 30.0,
            },
        ]
    }
    with respx.mock:
        respx.get(url__startswith="https://brapi.dev").mock(
            return_value=httpx.Response(200, json=resposta)
        )
        assert concentracao_setorial.collect_and_save() is True

    data = get_latest_concentracao_setorial_data()
    assert data is not None
    assert data.setor_destaque == "Petróleo e gás"


def test_setores_em_portugues():
    for setor in concentracao_setorial.SETOR_MAP.values():
        assert setor not in {"Finance", "Utilities", "Unknown"}


def test_snapshot_expoe_concentracao_setorial(setup_db):
    from fastapi.testclient import TestClient

    from app.main import app

    _salvar("Financeiro", 1.25)
    data = TestClient(app).get("/api/snapshot").json()
    painel = data["paineis"]["concentracao_setorial"]
    assert painel["setor_destaque"] == "Financeiro"
    assert painel["variacao_media"] == pytest.approx(1.25)
    assert painel["ha_setor_em_alta"] is True
    assert painel["fonte"] == "brapi"
    assert painel["coletado_em"]


def test_sem_setor_em_alta_a_tela_nao_chama_queda_de_destaque(setup_db):
    from fastapi.testclient import TestClient

    from app.main import app

    _salvar("Mineração", -0.4)
    html = TestClient(app).get("/").text
    assert "Nenhum setor em alta" in html
    assert "Melhor média: Mineração, -0,40%" in html
    snapshot = TestClient(app).get("/api/snapshot").json()
    assert snapshot["paineis"]["concentracao_setorial"]["ha_setor_em_alta"] is False
