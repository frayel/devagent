"""Aceite da spec 160: apetite a risco aqui e lá fora não usam o mesmo nome.

Sem internet: os snapshots são gravados direto no banco temporário do `setup_db`.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app import database as db
from app.main import app
from devagent.aceite import exigir_spec_done

pytestmark = pytest.mark.usefixtures("setup_db")


@pytest.fixture(autouse=True)
def _spec_done():
    exigir_spec_done("160")


def _gravar(status: str | None = "Apetite a Risco", apetite: bool = True) -> None:
    agora = datetime.now(timezone.utc)
    if status is not None:
        db.save_clima_global_data(
            db.ClimaGlobalData(
                timestamp=agora, sp500_pct=1.0, vix_pct=-3.0, status=status
            )
        )
    if apetite:
        db.save_apetite_risco_data(
            db.ApetiteRiscoData(timestamp=agora, estado="Defensivo", diferenca=-0.80)
        )


def _card_clima(html: str) -> str:
    m = re.search(
        r'<section class="painel[^"]*painel-clima-global[^"]*">(.*?)</section>',
        html,
        re.S,
    )
    assert m, "card do Clima Global não encontrado"
    return m.group(0)


def _texto_visivel(html: str) -> str:
    sem_comentarios = re.sub(r"<!--.*?-->", "", html, flags=re.S)
    sem_scripts = re.sub(
        r"<(script|style)\b.*?</\1>", "", sem_comentarios, flags=re.S | re.I
    )
    return re.sub(r"<[^>]*>", " ", sem_scripts)


def test_rotulos_distintos_e_estado_tomando_risco():
    _gravar()
    html = TestClient(app).get("/").text
    assert "Apetite aqui" in html
    assert "Apetite lá fora" in html
    card = _card_clima(html)
    assert re.search(r'class="texto-alta[^"]*">\s*Tomando risco', card)
    assert "Apetite a Risco" not in _texto_visivel(html)


@pytest.mark.parametrize(
    ("status", "texto", "classe"),
    [
        ("Aversão a Risco", "Defensivo", "texto-baixa"),
        ("Neutro", "Neutro", "texto-neutro"),
        ("xyz", "Neutro", "texto-neutro"),
    ],
)
def test_mapeamento_do_estado(status, texto, classe):
    _gravar(status)
    card = _card_clima(TestClient(app).get("/").text)
    assert re.search(rf'class="{classe}[^"]*">\s*{texto}', card)
    assert "xyz" not in _texto_visivel(card)


def test_metodo_do_clima_global_tem_os_cortes():
    _gravar()
    card = _card_clima(TestClient(app).get("/").text)
    m = re.search(r'<div class="metodo">(.*?)</div>', card, re.S)
    assert m, "ⓘ do Clima Global ausente"
    metodo = m.group(1)
    for trecho in ("2%", "3%", "0,5%", "ES=F", "^VIX"):
        assert trecho in metodo


def test_card_nao_usa_destaque():
    _gravar()
    card = _card_clima(TestClient(app).get("/").text)
    assert not re.search(r'class="[^"]*\bdestaque\b', card)


def test_contrato_do_snapshot_inalterado():
    _gravar()
    paineis = TestClient(app).get("/api/snapshot").json()["paineis"]
    assert paineis["clima_global"]["status"] == "Apetite a Risco"
    assert paineis["apetite_risco"]["estado"] == "Defensivo"


def test_sem_clima_global_card_escondido_e_mare_com_apetite_aqui():
    _gravar(status=None)
    html = TestClient(app).get("/").text
    card = _card_clima(html)
    assert "escondido" in card.split(">", 1)[0]
    assert "Apetite lá fora" not in card
    assert "Apetite aqui" in html
