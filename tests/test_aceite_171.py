"""Aceite da spec 171: a página baixa só o Plotly que desenha linhas.

Sem internet: confere o template, o cabeçalho CSP e os tipos de traço
usados no front. Baixar a CDN e comparar o hash é invariante do auditor.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from devagent.aceite import exigir_spec_done

RAIZ = Path(__file__).resolve().parent.parent / "app"
TEMPLATES = RAIZ / "templates"
STATIC = RAIZ / "static"

HTMX_SRC = "https://unpkg.com/htmx.org@1.9.10/dist/htmx.min.js"
PLOTLY_SRC = "https://cdn.plot.ly/plotly-basic-2.27.0.min.js"
PLOTLY_SRI = "sha384-C21rxKmXDHRC0bKRfO4BhLiAheJB5GEbL2ohT8ER/IW4/oXhpHW1iygb4d6p7vsb"
TRACOS_DO_PACOTE = {"scatter", "bar", "pie"}

_TAG = re.compile(r"<script\b[^>]*>", re.IGNORECASE)
_ATTR = re.compile(r'([\w-]+)\s*=\s*"([^"]*)"')
_TYPE = re.compile(r"""type:\s*['"](\w+)['"]""")


@pytest.fixture(autouse=True)
def _spec_done():
    exigir_spec_done("171")


def _fontes_script_src(csp: str) -> list[str]:
    for diretiva in csp.split(";"):
        partes = diretiva.split()
        if partes and partes[0] == "script-src":
            return partes[1:]
    raise AssertionError(f"CSP sem script-src: {csp}")


def test_pacote_basico_com_integridade() -> None:
    html = (TEMPLATES / "base.html").read_text(encoding="utf-8")
    plotly = [
        attrs
        for attrs in (dict(_ATTR.findall(tag)) for tag in _TAG.findall(html))
        if attrs.get("src", "").startswith("https://cdn.plot.ly/")
    ]
    assert len(plotly) == 1, plotly
    assert plotly[0]["src"] == PLOTLY_SRC
    assert plotly[0].get("integrity") == PLOTLY_SRI
    assert plotly[0].get("crossorigin") == "anonymous"


def test_csp_casa_com_o_pacote_basico() -> None:
    with TestClient(app) as client:
        csp = client.get("/healthz").headers["Content-Security-Policy"]
    assert _fontes_script_src(csp) == ["'self'", HTMX_SRC, PLOTLY_SRC]
    assert "plotly-strict" not in csp


def test_so_tracos_do_pacote() -> None:
    arquivos = sorted(STATIC.glob("*.js")) + sorted(TEMPLATES.glob("*.html"))
    achados = [
        (arquivo.name, nome)
        for arquivo in arquivos
        for nome in _TYPE.findall(arquivo.read_text(encoding="utf-8"))
    ]
    assert achados, "nenhum `type:` de traço encontrado: regex quebrada?"
    fora = [a for a in achados if a[1] not in TRACOS_DO_PACOTE]
    assert not fora, (
        f"traço fora do plotly-basic: {fora}; troque o pacote em base.html e no CSP"
    )
