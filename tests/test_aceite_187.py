"""Aceite da spec 187: classe nova sem estilo reprova o teste.

Sem rede e sem servidor: as funções puras de `tests/test_classes_com_estilo.py`
com textos montados aqui, e a regra rodada contra os arquivos reais.
"""

from __future__ import annotations

import pytest

from devagent.aceite import exigir_spec_done
from tests.test_classes_com_estilo import (
    SEM_ESTILO_CONHECIDAS,
    _arquivos_reais,
    classes_dos_templates,
    citadas_no_js,
    nomes_validos,
    problemas,
    seletores_do_css,
    sem_blocos,
    sem_estilo,
    sem_expressoes,
)

TEMPLATE = (
    '<span class="badge {% if ok %}badge-positivo{% else %}badge-negativo'
    '{% endif %} g-faixa-{{ n }}">x</span>'
)
VALOR = (
    "badge {% if ok %}badge-positivo{% else %}badge-negativo{% endif %} g-faixa-{{ n }}"
)
CSS = (
    ".badge-confianca { color: red } "
    "@media (max-width: 600px) { .badge-positivo { margin: 0.5rem } }"
)


@pytest.fixture(autouse=True)
def _spec_done():
    exigir_spec_done("187")


def test_exemplo_da_spec_passo_a_passo():
    passo1 = sem_expressoes(VALOR)
    assert passo1 == (
        "badge {% if ok %}badge-positivo{% else %}badge-negativo{% endif %} g-faixa-\x00"
    )
    passo2 = sem_blocos(passo1)
    # A spec escreve três espaços depois de `badge`; o método dá dois ("badge "
    # mais o espaço do `{% if %}`). O que o aceite pede é o conjunto do passo 3.
    assert passo2 == "badge  badge-positivo badge-negativo  g-faixa-\x00"
    assert "badge-positivobadge-negativo" not in passo2
    assert nomes_validos(passo2) == {"badge", "badge-positivo", "badge-negativo"}

    usos = classes_dos_templates({"x.html": TEMPLATE})
    assert set(usos) == {"badge", "badge-positivo", "badge-negativo"}
    assert seletores_do_css(CSS) == {"badge-confianca", "badge-positivo"}
    assert sem_estilo(usos, CSS, "") == {"badge", "badge-negativo"}

    conhecidas = {"badge": "gancho"}
    erros = problemas(usos, CSS, "", conhecidas)
    assert len(erros) == 1 and "badge-negativo" in erros[0]
    conhecidas["badge-negativo"] = "gancho"
    assert problemas(usos, CSS, "", conhecidas) == []
    erros = problemas(usos, CSS + " .badge { }", "", conhecidas)
    assert len(erros) == 1 and "`badge`" in erros[0] and "vencida" in erros[0]


def test_media_com_varias_regras_conta_e_numeros_nao_viram_seletor():
    css = (
        "@media (max-width: 600px) { .um { margin: 0.5rem } .dois { padding: 1.25em } }"
    )
    seletores = seletores_do_css(css)
    assert seletores == {"um", "dois"}
    assert "5rem" not in seletores and "25em" not in seletores


def test_classe_citada_no_js_nao_reprova_mas_prefixo_nao_salva():
    js = 'document.querySelector(".voltar-hoje"); const voltar = 1;'
    usos = {"voltar-hoje": {"x.html"}, "voltar-ontem": {"x.html"}}
    assert citadas_no_js(usos, js) == {"voltar-hoje"}
    erros = problemas(usos, "", js, {})
    assert len(erros) == 1 and "voltar-ontem" in erros[0]


def test_classe_nova_sem_estilo_reprova_citando_classe_e_template():
    usos = classes_dos_templates({"painel.html": '<div class="sem-efeito">'})
    erros = problemas(usos, "", "", {})
    assert len(erros) == 1
    assert "sem-efeito" in erros[0] and "painel.html" in erros[0]


def test_excecao_vencida_reprova():
    conhecidas = {"sumiu": "x", "ganhou": "x"}
    usos = {"ganhou": {"a.html"}}
    erros = problemas(usos, ".ganhou { color: red }", "", conhecidas)
    assert len(erros) == 2
    assert any("`sumiu`" in e for e in erros)
    assert any("`ganhou`" in e for e in erros)


def test_regra_passa_nos_arquivos_reais_e_lista_nao_cresce():
    templates, css, js = _arquivos_reais()
    assert (
        problemas(classes_dos_templates(templates), css, js, SEM_ESTILO_CONHECIDAS)
        == []
    )
    assert len(SEM_ESTILO_CONHECIDAS) <= 43
