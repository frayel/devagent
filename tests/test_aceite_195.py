"""Aceite da spec 195: Depois de cada faixa sai de /mare e vai para o painel geral.

Sem rede: reaproveita os fixtures da spec 183 (`calendario_fixo` e o
`mare_historico` sintético) e grava o Motores do Índice no banco temporário.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from app.database import MotoresIndiceData, save_motores_indice_data
from devagent.aceite import exigir_spec_done
from tests.test_aceite_183 import (
    _cliente,
    _gravar_historico,
    _gravar_mare,
    _historico_sintetico,
)

TEMPLATES = Path(__file__).resolve().parents[1] / "app" / "templates"


@pytest.fixture(autouse=True)
def _spec_done():
    exigir_spec_done("195")


@pytest.fixture
def calendario_fixo(monkeypatch):
    """O mesmo calendário da spec 183: pregão de 06/10/2026, mercado fechado."""

    class Mercado:
        def mercado_aberto(self, dt):
            return False

        def pregao_corrente(self, dt):
            return date(2026, 10, 6)

        def ultimo_pregao_fechado(self, dt):
            return date(2026, 10, 6)

    monkeypatch.setattr("app.main.calendario", Mercado())
    monkeypatch.setattr(
        "app.main.obter_pregoes_disponiveis", lambda *a, **k: ["2026-10-06"]
    )


def _gravar_motores() -> None:
    save_motores_indice_data(
        MotoresIndiceData(
            timestamp=datetime(2026, 10, 6, 17, 30, tzinfo=timezone.utc),
            motores_json=json.dumps([{"nome": "Financeiro", "variacao": 1.2}]),
            fonte="yfinance",
            pregao_data="2026-10-06",
        )
    )


def _secoes(html: str) -> list[tuple[str, str]]:
    """(classes, título) de cada `section.painel`, na ordem do HTML."""
    return [
        (m.group(1), m.group(2))
        for m in re.finditer(
            r'<section class="([^"]*\bpainel\b[^"]*)">\s*<div class="cab">\s*<h2>([^<]*)</h2>',
            html,
        )
    ]


def _quadro(html: str) -> tuple[int, str]:
    secoes = _secoes(html)
    i = next(i for i, (_, t) in enumerate(secoes) if t == "Depois de cada faixa")
    return i, secoes[i][0]


def test_mare_so_com_o_card(calendario_fixo):
    _gravar_historico(_historico_sintetico())
    _gravar_mare(30)
    html = _cliente().get("/mare").text
    assert "Depois de cada faixa" not in html
    assert "mare-memoria" not in html
    assert len(re.findall(r'<section class="[^"]*\bpainel\b', html)) == 1


def test_painel_geral_com_o_quadro(calendario_fixo):
    _gravar_historico(_historico_sintetico())
    _gravar_mare(30)  # Medo hoje
    cliente = _cliente()
    mem = cliente.get("/api/snapshot").json()["paineis"]["mare"]["memoria"]
    medo = next(f for f in mem["faixas"] if f["faixa"] == "Medo")
    html = cliente.get("/").text
    assert "Depois de cada faixa" in html
    de = date.fromisoformat(mem["de"]).strftime("%d/%m/%Y")
    ate = date.fromisoformat(mem["ate"]).strftime("%d/%m/%Y")
    assert (
        f"Nos {medo['casos']} pregões entre {de} e {ate} em que a Maré fechou em Medo"
    ) in html
    assert re.search(
        r'class="mare-memoria-hoje">\s*<th scope="row">Medo <span class="selo">hoje</span>',
        html,
    )
    _, classes = _quadro(html)
    for c in ("painel-memoria-mare", "visao-macro", "visao-geral"):
        assert c in classes.split()
    # A classe não casa com o card da Maré (spec 173).
    assert not re.search(r"\bpainel-mare\b", classes)


def test_posicao_com_motores(calendario_fixo):
    _gravar_historico(_historico_sintetico())
    _gravar_mare(30)
    _gravar_motores()
    html = _cliente().get("/").text
    secoes = _secoes(html)
    i, classes = _quadro(html)
    motores_classes, motores_titulo = secoes[i - 1]
    assert motores_titulo == "Motores do Índice"
    assert "escondido" not in motores_classes.split()
    assert "span-8" in motores_classes.split()
    assert "span-4" in classes.split()


def test_posicao_sem_motores(calendario_fixo):
    _gravar_historico(_historico_sintetico())
    _gravar_mare(30)
    secoes = _secoes(_cliente().get("/").text)
    i = next(i for i, (_, t) in enumerate(secoes) if t == "Depois de cada faixa")
    motores_classes, motores_titulo = secoes[i - 1]
    assert motores_titulo == "Motores do Índice"
    assert "escondido" in motores_classes.split()
    assert "span-12" in secoes[i][0].split()


def test_em_formacao_sem_historico(calendario_fixo):
    _gravar_mare(30)
    html = _cliente().get("/").text
    _quadro(html)
    assert "Memória em formação" in html
    assert "mare-memoria-tabela" not in html


def test_fora_do_seletor(calendario_fixo):
    _gravar_historico(_historico_sintetico())
    _gravar_mare(30)
    assert "Depois de cada faixa" not in _cliente().get("/mare/card?nivel=ondas").text


def test_data_passada_sem_registro(calendario_fixo, monkeypatch):
    monkeypatch.setattr(
        "app.main.obter_pregoes_disponiveis",
        lambda *a, **k: ["2026-10-06", "2026-10-05"],
    )
    _gravar_mare(30)
    resposta = _cliente().get("/?data=2026-10-05")
    assert resposta.status_code == 200
    html = resposta.text
    secoes = _secoes(html)
    _, classes = _quadro(html)
    assert "painel-memoria-mare" in classes.split()
    # O trecho do quadro mostra o estado sem registro, sem frase nem tabela.
    inicio = html.index("<h2>Depois de cada faixa</h2>")
    fim = html.index("</section>", inicio)
    trecho = html[inicio:fim]
    assert "Sem registro neste pregão" in trecho
    assert "Memória em formação" not in trecho
    assert "mare-memoria-tabela" not in trecho
    assert len(secoes) > 1


def test_uma_fonte_so():
    com_tabela = sorted(
        p.name
        for p in TEMPLATES.rglob("*.html")
        if "mare-memoria-tabela" in p.read_text(encoding="utf-8")
    )
    assert com_tabela == ["componentes.html"]
