"""Aceite da spec 176: a primeira dobra da Visão Geral sem espaço vazio.

Os gauges de Apetite aqui e Rotação saem do card da Maré para um card próprio,
"Apetite e rotação", ao lado do Clima Global (agora `span-4`). A Maré ocupa duas
linhas da grade e o Ibovespa fica com a altura do próprio conteúdo. Tudo sem
internet: o HTML vem do `TestClient` sobre o banco de demonstração do
`make telas`, e as medidas, do Chromium do ambiente com a rede abortada.
"""

from __future__ import annotations

import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.database
from devagent.aceite import exigir_spec_done

RAIZ = Path(__file__).resolve().parents[1]
STATIC = RAIZ / "app" / "static"

METODO = (
    "Apetite aqui: variação do dia do SMAL11 menos a do Ibovespa, em pontos "
    "percentuais. Tomando risco acima de +0,1 p.p., Defensivo abaixo de −0,1 p.p., "
    "Neutro no resto. Rotação: média da variação do dia de ITUB4, BBDC4 e BBAS3 "
    "menos a de VALE3, PETR4 e PRIO3. Para Bancos quando os bancos sobem mais de "
    "0,5% e as commodities caem mais de 0,5%; Para Commodities no inverso; Neutra "
    "no resto. O apetite aqui e o lá fora (card Clima Global) são medidas "
    "diferentes e podem divergir."
)

APETITE = {
    "time": "18/11/2026 11:05:00 BRT",
    "fonte": "fonte-apetite-176",
    "estado": "Tomando risco",
    "diferenca": 0.8,
}
ROTACAO = {
    "estado": "Para Bancos",
    "var_bancos": 1.0,
    "var_commodities": -0.5,
    "diferenca": 1.5,
    "time": "18/11/2026 11:06:00 BRT",
    "coletado_em": datetime(2026, 11, 18, 14, 6, tzinfo=timezone.utc),
    "fonte": "fonte-rotacao-176",
}


def test_aceite_176_spec_done():
    exigir_spec_done("176")


def _semear() -> None:
    """Banco de demonstração do `scripts/telas.py`, no banco temporário do teste."""
    sys.path.insert(0, str(RAIZ / "scripts"))
    try:
        import telas
    finally:
        sys.path.remove(str(RAIZ / "scripts"))
    telas._semear(app.database.DB_PATH)


@pytest.fixture
def banco_completo():
    _semear()


@pytest.fixture
def com_mocks(banco_completo, monkeypatch):
    monkeypatch.setattr("app.main.get_apetite_risco_view_data", lambda: dict(APETITE))
    monkeypatch.setattr("app.main.get_rotacao_capital_view", lambda: dict(ROTACAO))


def _home() -> str:
    from app.main import app as aplicacao

    resposta = TestClient(aplicacao).get("/")
    assert resposta.status_code == 200
    return resposta.text


def _secao(pagina: str, classe: str) -> str | None:
    m = re.search(
        r'<section class="painel[^"]*\b%s\b[^"]*">(.*?)</section>' % re.escape(classe),
        pagina,
        re.S,
    )
    return m.group(0) if m else None


# --- HTML ------------------------------------------------------------------------


def test_card_novo_com_metodo_rodape_e_gauges(com_mocks):
    pagina = _home()
    card = _secao(pagina, "painel-apetite-rotacao")
    assert card, "card Apetite e rotação ausente"
    abertura = card[: card.index(">")]
    for classe in ("span-4", "visao-macro", "visao-geral"):
        assert re.search(r"\b%s\b" % classe, abertura), classe
    assert "Apetite e rotação" in card
    assert METODO in card
    assert (
        "Fonte fonte-apetite-176 · 18/11/2026 11:05:00 BRT"
        " · Rotação: fonte-rotacao-176 · 18/11/2026 11:06:00 BRT"
    ) in card
    assert "SMLL − IBOV" in card
    assert "Bancos - Cmdts" in card


def test_mare_perde_os_gauges_e_clima_vira_span_4(com_mocks):
    pagina = _home()
    mare = _secao(pagina, "painel-mare")
    assert mare
    assert "SMLL − IBOV" not in mare
    assert "Bancos - Cmdts" not in mare
    assert "bancos − commodities" not in mare

    clima = _secao(pagina, "painel-clima-global")
    assert clima
    assert re.search(r"\bspan-4\b", clima[: clima.index(">")])
    assert "card Apetite e rotação" in clima
    assert "card Maré do mercado" not in clima

    assert pagina.index("painel-clima-global") < pagina.index("painel-apetite-rotacao")


def test_rodape_com_fonte_unica_quando_fontes_iguais(banco_completo, monkeypatch):
    monkeypatch.setattr("app.main.get_apetite_risco_view_data", lambda: dict(APETITE))
    rot = dict(ROTACAO, fonte=APETITE["fonte"])
    monkeypatch.setattr("app.main.get_rotacao_capital_view", lambda: rot)
    card = _secao(_home(), "painel-apetite-rotacao")
    assert card
    assert "Fonte fonte-apetite-176 · 18/11/2026 11:05:00 BRT</div>" in card
    assert "Rotação: fonte" not in card


def test_rodape_da_rotacao_sem_apetite(banco_completo, monkeypatch):
    monkeypatch.setattr("app.main.get_apetite_risco_view_data", lambda: None)
    monkeypatch.setattr("app.main.get_rotacao_capital_view", lambda: dict(ROTACAO))
    card = _secao(_home(), "painel-apetite-rotacao")
    assert card
    assert "Fonte fonte-rotacao-176 · 18/11/2026 11:06:00 BRT" in card
    assert "SMLL − IBOV" not in card
    assert "Bancos - Cmdts" in card


def test_sem_apetite_e_sem_rotacao_o_card_nao_aparece(banco_completo, monkeypatch):
    monkeypatch.setattr("app.main.get_apetite_risco_view_data", lambda: None)
    monkeypatch.setattr("app.main.get_rotacao_capital_view", lambda: None)
    assert "painel-apetite-rotacao" not in _home()


def test_escala_junto_de_cada_gauge_do_ibovespa(com_mocks):
    ibov = _secao(_home(), "painel-ibovespa")
    assert ibov
    assert ibov.count('class="g-escala') == 2
    gauges = re.search(r'<div class="gauges espaco-topo">(.*)', ibov, re.S)
    assert gauges
    # Cada escala vem logo depois do seu gauge, dentro do mesmo <div>.
    for rotulo in ("MM21", "MM200"):
        trecho = gauges.group(1).split(rotulo, 1)[1]
        antes_do_proximo = re.split(r"\n\s*<div>", trecho, maxsplit=1)[0]
        assert 'class="g-escala' in antes_do_proximo, rotulo


# --- Navegador -------------------------------------------------------------------

PLOTLY_FALSO = """
window.Plotly = {
  newPlot: function () { return Promise.resolve(); },
  react: function () { return Promise.resolve(); },
  purge: function () {},
  Plots: { resize: function () {} },
};
"""

MEDIR = """() => {
  const r = (sel) => {
    const el = document.querySelector(sel);
    if (!el) return null;
    const b = el.getBoundingClientRect();
    return {topo: b.top, base: b.bottom, esq: b.left, dir: b.right};
  };
  const rod = document.querySelector('.painel-ibovespa > .rodape');
  const antes = rod.previousElementSibling.getBoundingClientRect();
  const gap = parseFloat(getComputedStyle(document.querySelector('main.grade')).rowGap);
  return {
    ibov: r('.painel-ibovespa'), mare: r('.painel-mare'),
    clima: r('.painel-clima-global'), apetite: r('.painel-apetite-rotacao'),
    vao: rod.getBoundingClientRect().top - antes.bottom, gap: gap,
    scroll: document.documentElement.scrollWidth, largura: window.innerWidth,
  };
}"""


def _medir(pagina: str, largura: int, altura: int) -> dict:
    from playwright.sync_api import sync_playwright

    css = (STATIC / "tema.css").read_text(encoding="utf-8")
    pagina = re.sub(r"<script\b[^>]*\bsrc=[^>]*>\s*</script>", "", pagina)
    pagina = re.sub(r'<link rel="stylesheet"[^>]*>', "", pagina)
    pagina = pagina.replace("</head>", f"<style>{css}</style></head>", 1)
    with sync_playwright() as p:
        navegador = p.chromium.launch(
            executable_path=os.environ.get("CHROMIUM_PATH") or None
        )
        try:
            aba = navegador.new_page(viewport={"width": largura, "height": altura})
            aba.route("**/*", lambda rota: rota.abort())
            aba.set_content(pagina)
            aba.add_script_tag(content=PLOTLY_FALSO)
            for nome in ("graficos.js", "ui.js"):
                aba.add_script_tag(content=(STATIC / nome).read_text(encoding="utf-8"))
            aba.evaluate(
                "document.dispatchEvent(new Event('DOMContentLoaded'));"
                "window.dispatchEvent(new Event('load'));"
            )
            aba.wait_for_timeout(300)
            return aba.evaluate(MEDIR)
        finally:
            navegador.close()


def test_primeira_dobra_a_1440(com_mocks):
    m = _medir(_home(), 1440, 900)
    assert m["vao"] <= 24, m
    assert abs(m["apetite"]["base"] - m["mare"]["base"]) <= 24, m
    assert abs(m["apetite"]["topo"] - m["clima"]["topo"]) <= 2, m
    assert abs(m["clima"]["topo"] - (m["ibov"]["base"] + m["gap"])) <= 2, m
    assert m["scroll"] <= m["largura"], m


def test_cards_a_direita_da_mare_a_1024(com_mocks):
    m = _medir(_home(), 1024, 900)
    for card in ("clima", "apetite"):
        assert m[card]["esq"] >= m["mare"]["dir"], (card, m)
    assert abs(m["clima"]["topo"] - m["mare"]["topo"]) <= 2, m
    assert abs(m["apetite"]["base"] - m["mare"]["base"]) <= 24, m
    assert m["scroll"] <= m["largura"], m


def test_ordem_em_uma_coluna_a_390(com_mocks):
    m = _medir(_home(), 390, 844)
    ordem = [m[c]["topo"] for c in ("ibov", "mare", "clima", "apetite")]
    assert ordem == sorted(ordem), m
    assert m["scroll"] <= m["largura"], m


# --- Card sozinho: as 8 colunas abaixo do Ibovespa não ficam com buraco ----------


def _abertura(pagina: str, classe: str) -> str:
    card = _secao(pagina, classe)
    assert card, classe
    return card[: card.index(">")]


def test_sem_apetite_e_rotacao_o_clima_ocupa_as_8_colunas(banco_completo, monkeypatch):
    monkeypatch.setattr("app.main.get_apetite_risco_view_data", lambda: None)
    monkeypatch.setattr("app.main.get_rotacao_capital_view", lambda: None)
    assert re.search(r"\bspan-8\b", _abertura(_home(), "painel-clima-global"))


def test_sem_clima_o_card_novo_ocupa_as_8_colunas(com_mocks, monkeypatch):
    monkeypatch.setattr("app.main.get_latest_clima_global_data", lambda *a, **k: None)
    assert re.search(r"\bspan-8\b", _abertura(_home(), "painel-apetite-rotacao"))
