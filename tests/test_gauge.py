"""Gauge para valores únicos (spec 026): cálculo, macro e painéis."""

from __future__ import annotations

import re
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app import gauge
from app.main import app, templates


def render(chamada: str) -> str:
    t = templates.env.from_string(
        '{% from "componentes.html" import gauge %}' + "{{ " + chamada + " }}"
    )
    return t.render()


@pytest.mark.parametrize(
    ("valor", "minimo", "maximo", "esperado"),
    [
        (63, 0, 100, 63),
        (-5, 0, 100, 0),
        (150, 0, 100, 100),
        (-1, -2, 2, 25),
        (7, 0, 10, 70),
    ],
)
def test_gauge_pct_corta_nos_limites(valor, minimo, maximo, esperado):
    assert gauge.gauge_pct(valor, minimo, maximo) == pytest.approx(esperado)


def test_escala_vazia_nao_divide_por_zero():
    assert gauge.gauge_pct(5, 3, 3) == 0


def test_numero_no_padrao_brasileiro():
    assert gauge.numero_br(-1.24, "{:+.2f}%") == "-1,24%"
    assert gauge.numero_br(1234.5, "{:,.1f}") == "1.234,5"
    assert gauge.numero_br(0.8, "{:+.2f} p.p.") == "+0,80 p.p."


def test_macro_simples_63_de_100():
    html = render('gauge(63, "em alta", 0, 100, "{:.0f}%")')
    assert 'role="img"' in html
    assert 'aria-label="em alta: 63%"' in html
    assert 'stroke-dasharray="63 100"' in html
    assert 'class="g-valor alta"' in html
    assert ">63%<" in html
    assert "stroke-dashoffset" not in html.split('class="g-trilho"')[1]


def test_macro_divergente_menos_um_em_dois():
    html = render('gauge(-1.0, "SMLL", -2, 2, "{:+.1f} p.p.", divergente=True)')
    assert 'stroke-dasharray="25 100"' in html
    assert 'stroke-dashoffset="-25"' in html
    assert 'class="g-valor baixa"' in html
    assert "-1,0 p.p." in html
    assert "g-zero" in html


def test_divergente_positivo_parte_do_topo():
    html = render('gauge(1.0, "x", -2, 2, "{:+.1f}", divergente=True)')
    assert 'stroke-dasharray="25 100"' in html
    assert 'stroke-dashoffset="-50"' in html
    assert 'class="g-valor alta"' in html


def test_fora_da_escala_corta_o_arco_e_mostra_o_valor_real():
    html = render('gauge(150, "x")')
    assert 'stroke-dasharray="100 100"' in html
    assert ">150<" in html
    assert "fora da escala" in html


def test_aria_label_tem_o_mesmo_numero_do_texto():
    html = render(
        'gauge(2.75, "Bancos", -3, 3, "{:+.2f} p.p.", divergente=True, resumo="Rotação")'
    )
    numero = re.search(r'class="v num">([^<]+)<', html).group(1)
    aria = re.search(r'aria-label="([^"]+)"', html).group(1)
    assert numero == "+2,75 p.p."
    assert numero in aria


def test_faixas_marcam_a_faixa_atual_com_agulha():
    html = render(
        'gauge(68, "Maré", faixas=["Pânico", "Medo", "Neutro", "Confiança", "Otimismo extremo"])'
    )
    assert html.count('class="g-faixa ') == 5
    assert "g-valor g-cor-4" in html
    assert ">Confiança<" in html
    assert 'transform="rotate(32.4 60 60)"' in html


def test_limite_inferior_pertence_a_faixa_de_cima():
    d = gauge.dados(80, "x", faixas=["a", "b", "c", "d", "e"])
    assert d is not None and d["faixa"] == "e"
    d = gauge.dados(20, "x", faixas=["a", "b", "c", "d", "e"])
    assert d is not None and d["faixa"] == "b"


def test_sem_valor_mostra_estado_indisponivel():
    html = render('gauge(None, "x")')
    assert "Dado indisponível" in html
    assert 'class="gauge' not in html


def test_svg_sem_cor_escrita():
    html = render('gauge(68, "x", faixas=["a", "b", "c", "d", "e"])')
    assert not re.search(r'(fill|stroke)="(#|rgb|var)', html)
    assert "style=" not in html


def _popular_banco() -> None:
    from app import database as db

    agora = datetime.now(timezone.utc)
    db.save_apetite_risco_data(
        db.ApetiteRiscoData(
            timestamp=agora, estado="Defensivo", diferenca=-0.8, fonte="yfinance"
        )
    )
    db.save_rotacao_capital_data(
        db.RotacaoCapitalData(
            timestamp=agora,
            estado="Para Bancos",
            var_bancos=1.1,
            var_commodities=-0.4,
            fonte="yfinance",
        )
    )


def test_pagina_mostra_os_gauges_dos_paineis(setup_db):
    _popular_banco()
    html = TestClient(app).get("/").text
    assert "Small caps menos Ibovespa hoje: -0,80 p.p." in html
    assert 'stroke-dashoffset="-30"' in html  # -0,8 em ±2: de 30 a 50
    assert "Variação de bancos menos commodities hoje: +1,50 p.p." in html
    assert "Para Commodities" in html and "Para Bancos" in html


def test_banco_de_demonstracao_tem_pelo_menos_seis_gauges(setup_db):
    """Critério de aceite da spec 026, com os dados de scripts/telas.py."""
    import app.database as db
    from scripts import telas

    telas._semear(db.DB_PATH)
    html = TestClient(app).get("/").text
    assert len(re.findall(r'class="gauge[ "]', html)) >= 6
