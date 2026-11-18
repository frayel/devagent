"""Aceite da spec 173: a Maré numa tela só dela, em /mare.

Sem internet. A leitura da Maré é gravada no banco temporário do teste, como em
`tests/test_mare.py`; o calendário e o seletor de datas são fixados como em
`tests/test_aceite_088.py`. O `TestClient` não entra no `lifespan` (não é usado
como gerenciador de contexto), então os coletores não rodam.
"""

from __future__ import annotations

import json
import os
import re
from datetime import date, datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.database import MareData, save_mare_data
from devagent.aceite import exigir_spec_done

RAIZ = Path(__file__).resolve().parents[1]
TEMPLATES = RAIZ / "app" / "templates"
AVISO = (
    "Conteúdo informativo gerado automaticamente. "
    "Não constitui recomendação de investimento."
)


def test_aceite_173_spec_done():
    exigir_spec_done("173")


@pytest.fixture(autouse=True)
def calendario_fixo(monkeypatch):
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


def _gravar() -> None:
    historico = [{"data": f"2026-09-{d:02d}", "valor": 40 + d} for d in range(1, 22)]
    save_mare_data(
        MareData(
            timestamp=datetime(2026, 10, 6, 17, 30, tzinfo=timezone.utc),
            valor=68,
            fluxo=74.2,
            calma=61.0,
            volume=67.4,
            ativos_json="[]",
            historico_json=json.dumps(historico),
            fonte="yfinance",
        )
    )


def _get(caminho: str) -> str:
    from app.main import app

    resposta = TestClient(app).get(caminho)
    assert resposta.status_code == 200
    assert resposta.headers["content-type"].startswith("text/html")
    return resposta.text


@pytest.fixture
def com_mare():
    _gravar()


def test_rota_mostra_so_o_card(com_mare):
    html = _get("/mare")
    assert html.count("painel-mare") == 1
    assert 'aria-label="Maré do mercado, de 0 a 100' in html
    assert html.count('class="comp"') == 3
    assert 'class="mare-componentes"' in html
    for proibido in (
        "<header",
        'class="menu"',
        "seletor-data",
        "rodape-novidades",
        "aviso-banco-efemero",
        "SMLL − IBOV",
        "bancos − commodities",
        "Rotação",
    ):
        assert proibido not in html, proibido


def test_aviso_legal_uma_vez(com_mare):
    assert _get("/mare").count(AVISO) == 1


def test_rodape_do_card_com_fonte_e_horario(com_mare):
    html = _get("/mare")
    m = re.search(r'<div class="rodape">Fonte yfinance · ([^<]+)</div>', html)
    assert m, "rodapé Fonte ... · horário ausente"
    assert "06/10/2026" in m.group(1)


def test_refresh_e_titulo_so_em_mare(com_mare):
    html = _get("/mare")
    assert '<meta http-equiv="refresh" content="900">' in html
    assert "<title>Maré do mercado · Painel B3</title>" in html
    assert 'http-equiv="refresh"' not in _get("/")


def test_sem_dado_fica_indisponivel(monkeypatch):
    monkeypatch.setattr("app.database.get_latest_mare_data", lambda *a, **k: None)
    html = _get("/mare")
    assert "painel-mare" in html
    assert "Dado indisponível agora." in html
    assert html.count(AVISO) == 1


def test_um_card_uma_fonte():
    com_componentes = [
        p.name for p in TEMPLATES.rglob("*.html") if "mare-componentes" in p.read_text()
    ]
    assert com_componentes == ["componentes.html"]
    for nome in ("index.html", "mare.html"):
        assert "card_mare(" in (TEMPLATES / nome).read_text(), nome


def test_painel_geral_tira_apetite_e_rotacao_do_card(com_mare, monkeypatch):
    """Spec 176: os gauges de Apetite e Rotação moram no card Apetite e rotação."""
    monkeypatch.setattr(
        "app.main.get_apetite_risco_view_data",
        lambda: {
            "time": "",
            "fonte": "teste",
            "estado": "Tomando risco",
            "diferenca": 0.8,
        },
    )
    monkeypatch.setattr(
        "app.main.get_rotacao_capital_view",
        lambda: {
            "estado": "Para Bancos",
            "var_bancos": 1.0,
            "var_commodities": -0.5,
            "diferenca": 1.5,
            "time": "",
            "coletado_em": datetime(2026, 10, 6, 17, 30, tzinfo=timezone.utc),
        },
    )
    html = _get("/")
    m = re.search(
        r'<section class="painel[^"]*\bpainel-mare\b[^"]*">(.*?)</section>', html, re.S
    )
    assert m, "card da Maré ausente no painel geral"
    card = m.group(1)
    assert 'aria-label="Maré do mercado, de 0 a 100' in card
    assert "SMLL − IBOV" not in card
    assert "bancos − commodities" not in card
    novo = re.search(
        r'<section class="painel[^"]*\bpainel-apetite-rotacao\b[^"]*">(.*?)</section>',
        html,
        re.S,
    )
    assert novo, "card Apetite e rotação ausente no painel geral"
    assert "SMLL − IBOV" in novo.group(1)
    assert "bancos − commodities" in novo.group(1)


# --- Centralização no navegador ------------------------------------------------


def _medir(html: str, largura: int, altura: int) -> dict:
    from playwright.sync_api import sync_playwright

    css = (RAIZ / "app" / "static" / "tema.css").read_text(encoding="utf-8")
    pagina = re.sub(r"<script\b[^>]*\bsrc=[^>]*>\s*</script>", "", html)
    pagina = re.sub(r'<link rel="stylesheet"[^>]*>', f"<style>{css}</style>", pagina)
    pagina = pagina.replace('<meta http-equiv="refresh" content="900">', "")
    with sync_playwright() as p:
        navegador = p.chromium.launch(
            executable_path=os.environ.get("CHROMIUM_PATH") or None
        )
        try:
            aba = navegador.new_page(viewport={"width": largura, "height": altura})
            aba.route("**/*", lambda rota: rota.abort())
            aba.set_content(pagina)
            return aba.evaluate(
                """() => {
                  const c = document.querySelector('.painel-mare').getBoundingClientRect();
                  const f = document.querySelector('footer').getBoundingClientRect();
                  return {
                    esq: c.left, dir: window.innerWidth - c.right,
                    topo: c.top, base: c.bottom, rodape: f.top,
                    janela: window.innerHeight,
                    scroll: document.documentElement.scrollWidth,
                    largura: window.innerWidth,
                  };
                }"""
            )
        finally:
            navegador.close()


@pytest.mark.parametrize("largura,altura", [(390, 844), (1440, 900)])
def test_card_no_centro_da_tela(com_mare, largura, altura):
    m = _medir(_get("/mare"), largura, altura)
    assert abs(m["esq"] - m["dir"]) <= 2, m
    assert m["scroll"] <= m["largura"], m
    if m["base"] - m["topo"] > m["janela"]:
        assert m["topo"] <= 20, m
    else:
        centro_card = (m["topo"] + m["base"]) / 2
        centro_area = min(m["rodape"], m["janela"]) / 2
        assert abs(centro_card - centro_area) <= 0.10 * m["janela"], m
    if largura < 480:
        assert m["esq"] >= 15, m
