import pytest
import respx
import httpx

from app.collectors import concentracao_setorial
from app.database import get_latest_concentracao_setorial_data


YAHOO = r"https://query[12]\.finance\.yahoo\.com.*"


def _spark(*cotacoes: tuple[str, float, float, int]) -> dict:
    """Resposta do spark do Yahoo: (símbolo, preço, fechamento anterior, volume)."""
    return {
        "spark": {
            "result": [
                {
                    "symbol": f"{simbolo}.SA",
                    "response": [
                        {
                            "meta": {
                                "regularMarketPrice": preco,
                                "chartPreviousClose": anterior,
                                "regularMarketVolume": volume,
                            }
                        }
                    ],
                }
                for simbolo, preco, anterior, volume in cotacoes
            ]
        }
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


def test_coleta_concentracao_setorial_pelo_yahoo(setup_db):
    resposta = _spark(
        ("PETR4", 30.5, 30.0, 1000),
        ("VALE3", 61.2, 60.0, 2000),
        ("ITUB4", 25.0, 24.5, 5000),
    )
    with respx.mock:
        respx.get(url__regex=YAHOO).mock(
            return_value=httpx.Response(200, json=resposta)
        )
        assert concentracao_setorial.collect_and_save() is True

    data = get_latest_concentracao_setorial_data()
    assert data is not None
    assert data.fonte == "yfinance"
    # VALE3 sobe 2,0%, PETR4 1,67%, ITUB4 2,04%: Financeiro lidera.
    assert data.setor_destaque == "Financeiro"
    assert data.variacao_media == pytest.approx(2.0408, abs=1e-3)


def test_coleta_concentracao_setorial_com_yfinance(
    mock_yfinance_response, monkeypatch, setup_db
):
    with respx.mock:
        respx.get(url__regex=r"https://query[12]\.finance\.yahoo\.com.*").mock(
            return_value=httpx.Response(200, json=mock_yfinance_response)
        )

        sucesso = concentracao_setorial.collect_and_save()
        assert sucesso is True

        data = get_latest_concentracao_setorial_data()
        assert data is not None
        assert data.fonte == "yfinance"


def test_coleta_concentracao_setorial_falha_total(monkeypatch, setup_db):
    with respx.mock:
        respx.get(url__regex=r"https://query[12]\.finance\.yahoo\.com.*").mock(
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
            fonte="yfinance",
        )
    )


def test_acao_fora_do_mapa_nao_vira_setor(monkeypatch, setup_db):
    """Um ticker sem setor conhecido não pode ser apontado como líder."""
    resposta = _spark(("XPTO3", 20.0, 10.0, 100), ("PETR4", 30.3, 30.0, 100))
    with respx.mock:
        respx.get(url__regex=YAHOO).mock(
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
    assert painel["fonte"] == "yfinance"
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
