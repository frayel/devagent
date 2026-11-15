"""Nenhum painel pode mostrar marcação HTML como texto (ex.: "<span>+591%</span>").

O primeiro teste deste arquivo só procurava `&lt;span`. Em 15/11/2026 o card
Fator Peso Pesado exibia `<div class="texto-2 ...">` na tela. O template montava `'<div>' ~ (frase | e) ~ '</div>'`: com autoescape,
o `~` com um operando `Markup` escapa os literais, e o `| safe` do fim chegava
tarde. Este teste renderiza as páginas com o banco de demonstração do
`make telas` e reprova qualquer tag escapada (`&lt;div`, `&lt;/span` etc.).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.database

RAIZ = Path(__file__).resolve().parents[1]

# `&lt;` seguido de nome de tag (ou `/`): HTML que virou texto. `&lt;=2%` passa.
TAG_ESCAPADA = re.compile(r"&lt;/?[a-zA-Z][a-zA-Z0-9-]*(\s|&gt;|/|&#34;|$)")

PAGINAS = ["/", "/?vazios=1", "/sistema", "/novidades", "/consultor"]


def _semear() -> None:
    sys.path.insert(0, str(RAIZ / "scripts"))
    try:
        import telas
    finally:
        sys.path.remove(str(RAIZ / "scripts"))
    telas._semear(app.database.DB_PATH)


def _tags_escapadas(html: str) -> list[str]:
    achados = []
    for m in TAG_ESCAPADA.finditer(html):
        inicio = max(0, m.start() - 60)
        achados.append(html[inicio : m.end() + 60].replace("\n", " "))
    return achados


def test_pagina_nao_mostra_tags_escapadas():
    _semear()
    from app.main import app as aplicacao

    html = TestClient(aplicacao).get("/").text
    assert "&lt;span" not in html
    assert "&lt;/span" not in html


@pytest.fixture
def cliente():
    _semear()
    from app.main import app as aplicacao

    return TestClient(aplicacao)


@pytest.mark.parametrize("rota", PAGINAS)
def test_pagina_sem_html_escapado(cliente, rota):
    resposta = cliente.get(rota)
    assert resposta.status_code == 200
    assert _tags_escapadas(resposta.text) == []


def _secao_fator(html: str) -> str:
    m = re.search(r"Fator Peso Pesado</h2>(.*?)</section>", html, re.S)
    assert m, "card Fator Peso Pesado não encontrado"
    return m.group(1)


def test_fator_peso_pesado_renderiza_a_frase_como_html(cliente):
    secao = _secao_fator(cliente.get("/").text)
    assert '<div class="texto-2 espaco-topo-curto">As 5 maiores' in secao
    assert _tags_escapadas(secao) == []


def test_fator_peso_pesado_ainda_escapa_o_texto_da_frase(cliente, monkeypatch):
    from app.services import fator_peso_pesado

    monkeypatch.setattr(fator_peso_pesado, "frase", lambda *a: "a <b>b</b> & c")
    secao = _secao_fator(cliente.get("/").text)
    # A tag do template é HTML; o conteúdo da frase continua escapado.
    assert (
        '<div class="texto-2 espaco-topo-curto">a &lt;b&gt;b&lt;/b&gt; &amp; c</div>'
        in secao
    )


def test_detector_acha_o_defeito_de_15_11():
    defeito = "&lt;div class=&#34;texto-2 espaco-topo-curto&#34;&gt;As 5 maiores"
    assert _tags_escapadas(defeito)
    assert not _tags_escapadas("perto da mínima (&lt;=2%) e distante")
