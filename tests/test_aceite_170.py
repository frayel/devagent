"""Aceite da spec 170: o navegador recusa o Plotly alterado na CDN.

O htmx saiu na spec 172; o Plotly mora só em `index.html` desde então.

Sem internet: confere os templates e o cabeçalho CSP. Baixar as CDNs e
comparar o hash é invariante do auditor, não teste.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from devagent.aceite import exigir_spec_done

TEMPLATES = Path(__file__).resolve().parent.parent / "app" / "templates"

PLOTLY_SRC = "https://cdn.plot.ly/plotly-basic-2.27.0.min.js"
PLOTLY_SRI = "sha384-C21rxKmXDHRC0bKRfO4BhLiAheJB5GEbL2ohT8ER/IW4/oXhpHW1iygb4d6p7vsb"

_TAG = re.compile(r"<script\b[^>]*>", re.IGNORECASE)
_ATTR = re.compile(r'([\w-]+)\s*=\s*"([^"]*)"')
_SRI = re.compile(r"^sha384-[A-Za-z0-9+/]{64}$")


@pytest.fixture(autouse=True)
def _spec_done():
    exigir_spec_done("170")


def _scripts_externos(html: str) -> list[dict[str, str]]:
    tags = []
    for tag in _TAG.findall(html):
        attrs = dict(_ATTR.findall(tag))
        if attrs.get("src", "").startswith("http"):
            tags.append(attrs)
    return tags


def _todos_externos() -> list[tuple[str, dict[str, str]]]:
    return [
        (p.name, attrs)
        for p in sorted(TEMPLATES.glob("*.html"))
        for attrs in _scripts_externos(p.read_text(encoding="utf-8"))
    ]


def _fontes_script_src() -> list[str]:
    with TestClient(app) as client:
        csp = client.get("/healthz").headers["Content-Security-Policy"]
    for diretiva in csp.split(";"):
        partes = diretiva.split()
        if partes and partes[0] == "script-src":
            return partes[1:]
    raise AssertionError(f"CSP sem script-src: {csp}")


def test_toda_tag_externa_tem_integridade() -> None:
    externos = _todos_externos()
    assert externos, "nenhum script externo encontrado nos templates"
    for arquivo, attrs in externos:
        assert _SRI.match(attrs.get("integrity", "")), (arquivo, attrs)
        assert attrs.get("crossorigin") == "anonymous", (arquivo, attrs)


def test_valores_sao_os_da_tabela() -> None:
    index = _scripts_externos((TEMPLATES / "index.html").read_text(encoding="utf-8"))
    por_src = {a["src"]: a for a in index}
    assert por_src[PLOTLY_SRC]["integrity"] == PLOTLY_SRI


def test_nenhum_endereco_de_pacote() -> None:
    for arquivo, attrs in _todos_externos():
        assert not re.search(r"@[\w.\-]+/?$", attrs["src"]), (arquivo, attrs["src"])


def test_csp_restrito_ao_arquivo_do_plotly() -> None:
    fontes = _fontes_script_src()
    assert fontes == ["'self'", PLOTLY_SRC]
    assert "https://unpkg.com" not in fontes
    assert "https://cdn.plot.ly" not in fontes


def test_csp_e_template_casam() -> None:
    fontes = set(_fontes_script_src())
    for arquivo, attrs in _todos_externos():
        assert attrs["src"] in fontes, (arquivo, attrs["src"])
