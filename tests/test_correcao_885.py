"""Regressão da issue #885: toda página é legível de 360 a 1440 px.

Regra do `PRODUTO.md`, seção 6: a página nunca rola para o lado, nenhum
controle fica fora da tela e nenhum texto vaza da caixa. A checagem é a mesma
do `make telas` (`scripts/telas.py`), agora no CI: `/`, `/consultor` e
`/sistema` com os dados de demonstração, nas quatro larguras, com o seletor de
data no cabeçalho (no celular ele terminava em x = 487 px).

A página vem da aplicação de verdade (via `TestClient`) servida ao Chromium
headless em `http://painel.teste/`, como no teste da issue #883; requisições
externas (htmx, Plotly) são abortadas. O Chromium ausente falha o teste.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.database
from app.main import app as aplicacao

RAIZ = Path(__file__).resolve().parents[1]
BASE = "http://painel.teste"

sys.path.insert(0, str(RAIZ / "scripts"))
try:
    import telas
finally:
    sys.path.remove(str(RAIZ / "scripts"))


@pytest.fixture(scope="module")
def chromium():
    """Um Chromium para o módulo; o banco é refeito a cada teste (conftest)."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        nav = p.chromium.launch(executable_path=os.environ.get("CHROMIUM_PATH") or None)
        try:
            yield nav
        finally:
            nav.close()


@pytest.fixture
def navegador(chromium):
    """Banco de demonstração do `make telas` e a rota que serve a aplicação."""
    telas._semear(app.database.DB_PATH)
    cliente = TestClient(aplicacao)

    def _rota(rota) -> None:
        url = rota.request.url
        if not url.startswith(BASE + "/"):
            rota.abort()
            return
        resposta = cliente.get(url[len(BASE) :])
        rota.fulfill(
            status=resposta.status_code,
            headers={
                k: v for k, v in resposta.headers.items() if k != "content-length"
            },
            body=resposta.content,
        )

    return chromium, _rota


@pytest.mark.parametrize("caminho", [c for _, c in telas.PAGINAS])
@pytest.mark.parametrize("largura", sorted(w for w, _ in telas.TAMANHOS.values()))
def test_pagina_legivel_na_largura(navegador, caminho, largura):
    nav, rota = navegador
    altura = {w: h for w, h in telas.TAMANHOS.values()}[largura]
    aba = nav.new_page(viewport={"width": largura, "height": altura})
    try:
        aba.route("**/*", rota)
        aba.goto(BASE + caminho)
        aba.wait_for_load_state("domcontentloaded")
        aba.wait_for_timeout(200)
        if largura <= 390:
            # O seletor de data aparece no cabeçalho e cabe inteiro na tela.
            caixa = aba.locator("select.seletor-data").bounding_box()
            assert caixa is not None
            assert caixa["x"] >= 0 and caixa["x"] + caixa["width"] <= largura
        assert telas._vazamentos(aba) == []
    finally:
        aba.close()
