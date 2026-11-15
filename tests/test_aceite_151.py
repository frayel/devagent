"""Aceite da spec 151: a inflexão aparece uma vez só.

"Inflexão de Tendência" (rankings) e "Radar de Inflexão" (alertas) liam o mesmo
`radar_inflexao`. Fica só o segundo, com queda acumulada e variação de hoje, e
com os cortes publicados no ⓘ. Sem rede: o getter do banco é trocado por um
payload fixo e o relógio da página é congelado num pregão.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import app
from devagent.aceite import exigir_spec_done

client = TestClient(app)

BRT = timezone(timedelta(hours=-3))
# Pregão de segunda, 16/11/2026, 10:45 BRT; coleta fresca às 10:30.
AGORA = datetime(2026, 11, 16, 13, 45, tzinfo=timezone.utc)
FRESCO = datetime(2026, 11, 16, 10, 30, tzinfo=BRT)

TITULO = "Radar de Inflexão"
FRASES_VAZIAS = (
    "Nenhuma ação com inflexão no momento.",
    "Nenhuma inflexão detectada hoje.",
)


@dataclass
class _Snapshot:
    timestamp: datetime
    alertas_json: str
    fonte: str = "fonte-do-teste"


@pytest.fixture
def relogio(monkeypatch):
    class Relogio(datetime):
        @classmethod
        def now(cls, tz=None):  # type: ignore[override]
            return AGORA if tz is None else AGORA.astimezone(tz)

    monkeypatch.setattr("app.main.datetime", Relogio)


@pytest.fixture
def inflexao(monkeypatch, relogio):
    """Troca o snapshot do radar; devolve a função que define o payload."""
    estado: dict = {"snap": None}
    monkeypatch.setattr(
        "app.database.get_latest_radar_inflexao_data", lambda *a, **k: estado["snap"]
    )

    def definir(alertas: list | None) -> None:
        estado["snap"] = (
            None if alertas is None else _Snapshot(FRESCO, json.dumps(alertas))
        )

    return definir


def _html() -> str:
    resp = client.get("/")
    assert resp.status_code == 200
    return resp.text


def _card(html: str) -> str:
    achados = re.findall(
        rf'<section class="painel[^"]*">\s*<div class="cab">\s*<h2>{TITULO}</h2>.*?</section>',
        html,
        re.S,
    )
    assert len(achados) == 1, f"esperado um card {TITULO}, achados {len(achados)}"
    return achados[0]


def _sem_alerta(html: str) -> list[str]:
    m = re.search(r'<ul class="radares-sem-alerta">(.*?)</ul>', html, re.S)
    if not m:
        return []
    return [i.strip() for i in re.findall(r"<li>(.*?)</li>", m.group(1), re.S)]


def test_aceite_151_spec_done():
    exigir_spec_done("151")


def test_um_nome_aparece_uma_vez_com_as_duas_colunas(inflexao):
    inflexao([{"ticker": "XXXX3", "retorno_acumulado": -8.0, "variacao_hoje": 3.0}])
    html = _html()
    assert "Inflexão de Tendência" not in html
    assert html.count("XXXX3") == 1
    card = _card(html)
    assert "XXXX3" in card
    assert "-8,00%" in card
    assert "3,00%" in card
    assert "Queda" in card and "Hoje" in card


def test_metodo_publica_cortes_janela_e_fonte(inflexao):
    inflexao([{"ticker": "XXXX3", "retorno_acumulado": -8.0, "variacao_hoje": 3.0}])
    card = _card(_html())
    metodo = re.search(r'<div class="metodo">(.*?)</div>', card, re.S)
    assert metodo
    texto = metodo.group(1)
    assert "5%" in texto and "2%" in texto
    assert "16" in texto
    assert "Fonte fonte-do-teste" in card


def test_lista_vazia_sem_frase_de_lista_vazia(inflexao):
    inflexao([])
    html = _html()
    for frase in FRASES_VAZIAS:
        assert frase not in html
    assert "Inflexão de Tendência" not in html
    assert TITULO in _sem_alerta(html)


def test_sem_snapshot_e_indisponivel(inflexao):
    inflexao(None)
    html = _html()
    card = _card(html)
    assert "indisponível" in card
    for frase in FRASES_VAZIAS:
        assert frase not in html
    assert "XXXX3" not in html
    assert TITULO not in _sem_alerta(html)


def test_exemplo_da_spec(inflexao):
    """close[-16]=40, close[-2]=36, close[-1]=37,08: −10,00% e 3,00%."""
    acumulado = round((36.00 - 40.00) / 40.00 * 100, 2)
    hoje = round((37.08 - 36.00) / 36.00 * 100, 2)
    assert (acumulado, hoje) == (-10.0, 3.0)
    inflexao(
        [{"ticker": "XXXX3", "retorno_acumulado": acumulado, "variacao_hoje": hoje}]
    )
    card = _card(_html())
    assert "-10,00%" in card and "3,00%" in card
