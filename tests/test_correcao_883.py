"""Regressão da issue #883: o seletor de pregão troca a data e a aba sobrevive.

A página vem da aplicação de verdade (via `TestClient`, com os cabeçalhos dela,
inclusive a CSP) servida ao Chromium headless em `http://painel.teste/`; os
arquivos de `/static` também. Toda requisição externa (htmx, Plotly) é abortada,
como nos aceites das specs 146 e 156. O Chromium ausente falha o teste.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi.testclient import TestClient

import app.database
from app.main import app as aplicacao

RAIZ = Path(__file__).resolve().parents[1]
TEMPLATES = RAIZ / "app" / "templates"
BASE = "http://painel.teste"


def test_nenhum_template_tem_evento_inline():
    """A CSP não tem 'unsafe-inline': atributo `on*=` nunca roda no navegador."""
    achados = [
        f"{t.relative_to(RAIZ)}: {m.group(0)}"
        for t in sorted(TEMPLATES.rglob("*.html"))
        for m in re.finditer(r"\son[a-z]+\s*=", t.read_text(encoding="utf-8"))
    ]
    assert achados == []


@pytest.fixture
def banco(monkeypatch):
    """Banco de demonstração do `scripts/telas.py` e dois pregões no seletor."""
    sys.path.insert(0, str(RAIZ / "scripts"))
    try:
        import telas
    finally:
        sys.path.remove(str(RAIZ / "scripts"))
    telas._semear(app.database.DB_PATH)
    monkeypatch.setattr(
        "app.main.obter_pregoes_disponiveis",
        lambda *a, **k: ["2026-11-13", "2026-11-12"],
    )


@pytest.fixture
def navegador():
    from playwright.sync_api import sync_playwright

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

    with sync_playwright() as p:
        nav = p.chromium.launch(executable_path=os.environ.get("CHROMIUM_PATH") or None)
        try:
            aba = nav.new_page()
            aba.route("**/*", _rota)
            aba.csp = []  # violações de CSP vistas no console

            def _console(msg) -> None:
                if "Content Security Policy" in msg.text:
                    aba.csp.append(msg.text)

            aba.on("console", _console)
            yield aba
        finally:
            nav.close()


def _consulta(aba) -> dict[str, list[str]]:
    return parse_qs(urlsplit(aba.url).query)


def _aba_ativa(aba) -> str | None:
    return aba.evaluate(
        "(() => { const b = document.querySelector('.aba-btn.ativo[data-aba]');"
        " return b ? b.getAttribute('data-aba') : null; })()"
    )


def _outra_data(aba) -> str:
    valores = aba.eval_on_selector_all(
        "select.seletor-data option", "os => os.map(o => o.value)"
    )
    assert valores[1:] == ["2026-11-12"]
    return valores[1]


def _trocar_data(aba, valor: str) -> None:
    with aba.expect_navigation():
        aba.select_option("select.seletor-data", valor)
    aba.wait_for_load_state("domcontentloaded")


def test_trocar_data_navega_para_o_pregao(banco, navegador):
    navegador.goto(BASE + "/")
    valor = _outra_data(navegador)
    _trocar_data(navegador, valor)
    assert _consulta(navegador) == {"data": [valor]}
    assert "Você está vendo o fechamento de" in navegador.content()
    assert navegador.csp == []


def test_aba_vai_para_a_url_e_sobrevive_a_troca_de_data(banco, navegador):
    navegador.goto(BASE + "/")
    navegador.click(".aba-btn[data-aba='rankings']")
    # Sem recarregar: a URL muda só pelo history.replaceState.
    assert navegador.evaluate("performance.getEntriesByType('navigation').length") == 1
    assert _consulta(navegador) == {"aba": ["rankings"]}

    valor = _outra_data(navegador)
    _trocar_data(navegador, valor)
    assert _consulta(navegador) == {"data": [valor], "aba": ["rankings"]}
    assert _aba_ativa(navegador) == "rankings"

    # "Voltar para hoje" mantém a aba.
    with navegador.expect_navigation():
        navegador.click("a.voltar-hoje")
    assert _consulta(navegador) == {"aba": ["rankings"]}
    assert _aba_ativa(navegador) == "rankings"
    assert navegador.csp == []


def test_consultor_sem_violacao_de_csp(banco, navegador):
    navegador.goto(BASE + "/consultor")
    navegador.wait_for_timeout(200)
    assert navegador.csp == []
