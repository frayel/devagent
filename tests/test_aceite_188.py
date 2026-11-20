"""Aceite da spec 188: três radares montados à mão passam a usar a tabela comum.

Sem rede, com o SQLite temporário do `conftest`: os alertas do exemplo da spec
são gravados com os `save_*` dos três radares e a tela é lida por `GET /`.
O HTML de cada card é o trecho entre o `<h2>` dele e o `</section>` seguinte.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.database import (
    FalsoRompimentoData,
    RadarAnomaliasSpreadData,
    RadarDivergenciaVolumeData,
    save_falso_rompimento_data,
    save_radar_anomalias_spread_data,
    save_radar_divergencia_volume_data,
)
from app.main import app as aplicacao
from devagent.aceite import exigir_spec_done
from tests.test_aceite_150 import _historico
from tests.test_classes_com_estilo import SEM_ESTILO_CONHECIDAS

client = TestClient(aplicacao)

TITULOS = ("Anomalias de Spread", "Falso Rompimento", "Divergência Volume/Preço")
REMOVIDAS = (
    "ranking",
    "numero",
    "positivo",
    "negativo",
    "dado-indisponivel",
    "esq",
    "dir",
    "estado",
    "vazia",
    "normal",
    "icone",
)


@pytest.fixture(autouse=True)
def _spec_done():
    exigir_spec_done("188")


def _gravar(spread: list, falso: list, diverg: list) -> None:
    agora = datetime.now(timezone.utc)
    save_radar_anomalias_spread_data(
        RadarAnomaliasSpreadData(timestamp=agora, alertas_json=json.dumps(spread))
    )
    save_falso_rompimento_data(
        FalsoRompimentoData(timestamp=agora, alertas_json=json.dumps(falso))
    )
    save_radar_divergencia_volume_data(
        RadarDivergenciaVolumeData(timestamp=agora, alertas_json=json.dumps(diverg))
    )


def _exemplo() -> None:
    _gravar(
        [{"ticker": "PETR4", "spread_percent": (20.17 - 20.00) / 20.00 * 100}],
        [
            {"ticker": "VALE3", "variacao": -2.5, "var_volume": 80.0},
            {"ticker": "ITUB4", "variacao": -1.0, "var_volume": 0.0},
        ],
        [{"ticker": "WEGE3", "alta_acumulada": 5.0, "var_volume": -40.0}],
    )


def _card(html: str, titulo: str) -> str:
    ini = html.index(f"<h2>{titulo}</h2>")
    return html[ini : html.index("</section>", ini)]


def _celulas(card: str) -> list[tuple[str, str]]:
    """(classe, conteúdo sem tags e espaços extras) de cada `<td>`."""
    saida = []
    for classe, corpo in re.findall(r'<td class="([^"]*)">(.*?)</td>', card, re.S):
        saida.append((classe.split(), " ".join(re.sub(r"<[^>]+>", " ", corpo).split())))
    return saida


def _classes(card: str) -> set[str]:
    return {c for attr in re.findall(r'class="([^"]*)"', card) for c in attr.split()}


def _var(card: str, cor: str, texto: str) -> bool:
    padrao = rf'<span class="var {cor}">\s*{re.escape(texto)}\s*</span>'
    return re.search(padrao, card) is not None


def test_percentuais_com_cor_do_sinal():
    _exemplo()
    html = client.get("/").text
    falso = _card(html, "Falso Rompimento")
    assert _var(falso, "baixa", "▼ -2,50%")
    assert _var(falso, "alta", "▲ 80,00%")
    celulas = _celulas(falso)
    assert (["n"], "▼ -2,50%") in celulas
    assert (["n"], "▲ 80,00%") in celulas

    diverg = _card(html, "Divergência Volume/Preço")
    assert _var(diverg, "alta", "▲ 5,00%")
    assert _var(diverg, "baixa", "▼ -40,00%")


def test_sinal_zero_sai_neutro():
    _exemplo()
    falso = _card(client.get("/").text, "Falso Rompimento")
    assert _var(falso, "neutra", "■ 0,00%")
    assert (["n"], "■ 0,00%") in _celulas(falso)


def test_spread_sem_cor():
    _exemplo()
    spread = _card(client.get("/").text, "Anomalias de Spread")
    assert (["n"], "0,85%") in _celulas(spread)
    assert "var alta" not in spread and "var baixa" not in spread


def test_ticker_em_celula_tk():
    _exemplo()
    html = client.get("/").text
    esperados = {
        "Anomalias de Spread": ["PETR4"],
        "Falso Rompimento": ["VALE3", "ITUB4"],
        "Divergência Volume/Preço": ["WEGE3"],
    }
    for titulo, tickers in esperados.items():
        card = _card(html, titulo)
        assert '<tbody data-rank="' in card
        for tk in tickers:
            assert (["tk"], tk) in _celulas(card)


def test_sem_alerta_usa_vazio():
    _gravar([], [], [])
    html = client.get("/").text
    textos = {
        "Anomalias de Spread": "Spreads normais hoje.",
        "Falso Rompimento": "Nenhum falso rompimento detectado hoje.",
        "Divergência Volume/Preço": "Nenhuma divergência detectada hoje.",
    }
    for titulo, texto in textos.items():
        card = _card(html, titulo)
        assert re.search(rf'<div class="vazio">\s*{re.escape(texto)}\s*</div>', card)


def test_pregao_passado_sem_registro(monkeypatch):
    monkeypatch.setattr("app.main._get_seletor_context", _historico(monkeypatch))
    html = client.get("/?data=2026-11-18").text
    for titulo in TITULOS:
        card = _card(html, titulo)
        assert "Sem registro neste pregão" in card
        assert "agora" not in card and "Sem dados" not in card


@pytest.mark.parametrize("gravar", [_exemplo, lambda: _gravar([], [], []), None])
def test_nenhuma_classe_removida(gravar):
    if gravar:
        gravar()
    html = client.get("/").text
    for titulo in TITULOS:
        assert _classes(_card(html, titulo)).isdisjoint(REMOVIDAS)


def test_lista_de_divida_encolheu():
    assert set(REMOVIDAS).isdisjoint(SEM_ESTILO_CONHECIDAS)
    assert len(SEM_ESTILO_CONHECIDAS) <= 32
