"""Aceite da spec 172: cada página baixa só o script que usa.

Sem internet: confere os templates, o HTML renderizado de cada página e o
cabeçalho CSP. O `TestClient` não entra no `lifespan` (sem `with`), como nos
testes de rota de `test_consultor.py` e `test_aceite_123.py`.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import novidades
from devagent.aceite import exigir_spec_done

TEMPLATES = Path(__file__).resolve().parent.parent / "app" / "templates"

PLOTLY_SRC = "https://cdn.plot.ly/plotly-basic-2.27.0.min.js"
PLOTLY_SRI = "sha384-C21rxKmXDHRC0bKRfO4BhLiAheJB5GEbL2ohT8ER/IW4/oXhpHW1iygb4d6p7vsb"
SEM_GRAFICO = ["/consultor", "/sistema", "/novidades"]

_TAG = re.compile(r"<script\b[^>]*>", re.IGNORECASE)
_ATTR = re.compile(r'([\w-]+)(?:\s*=\s*"([^"]*)")?')

client = TestClient(app)


@pytest.fixture(autouse=True)
def _spec_done(monkeypatch, tmp_path):
    exigir_spec_done("172")
    monkeypatch.delenv("CONSULTOR_SENHA", raising=False)
    monkeypatch.setattr(novidades, "CAMINHO", tmp_path / "novidades.json")


def _scripts(html: str) -> list[dict[str, str]]:
    tags = []
    for tag in _TAG.findall(html):
        corpo = tag[len("<script") : -1]
        tags.append({nome.lower(): valor for nome, valor in _ATTR.findall(corpo)})
    return tags


def _html(rota: str) -> str:
    resp = client.get(rota)
    assert resp.status_code == 200, (rota, resp.status_code)
    return resp.text


def _fontes_script_src() -> list[str]:
    csp = client.get("/healthz").headers["Content-Security-Policy"]
    for diretiva in csp.split(";"):
        partes = diretiva.split()
        if partes and partes[0] == "script-src":
            return partes[1:]
    raise AssertionError(f"CSP sem script-src: {csp}")


def test_htmx_fora() -> None:
    for arquivo in sorted(TEMPLATES.glob("*.html")):
        assert "htmx" not in arquivo.read_text(encoding="utf-8"), arquivo.name
    csp = client.get("/healthz").headers["Content-Security-Policy"]
    assert "unpkg.com" not in csp
    assert "htmx" not in csp


def test_csp_so_com_o_plotly() -> None:
    assert _fontes_script_src() == ["'self'", PLOTLY_SRC]


def test_plotly_so_na_home() -> None:
    externos = [s for s in _scripts(_html("/")) if s.get("src", "").startswith("http")]
    assert len(externos) == 1, externos
    plotly = externos[0]
    assert plotly["src"] == PLOTLY_SRC
    assert plotly.get("integrity") == PLOTLY_SRI
    assert plotly.get("crossorigin") == "anonymous"
    assert "defer" in plotly

    for rota in SEM_GRAFICO:
        fora = [s for s in _scripts(_html(rota)) if s.get("src", "").startswith("http")]
        assert not fora, (rota, fora)


def _ordem(scripts: list[dict[str, str]], srcs: list[str]) -> list[dict[str, str]]:
    achados = [s for s in scripts if s.get("src") in srcs]
    assert [s["src"] for s in achados] == srcs, achados
    return achados


def test_ordem_e_defer() -> None:
    na_home = _ordem(
        _scripts(_html("/")), [PLOTLY_SRC, "/static/graficos.js", "/static/ui.js"]
    )
    assert all("defer" in s for s in na_home), na_home

    for rota in SEM_GRAFICO:
        locais = _ordem(_scripts(_html(rota)), ["/static/graficos.js", "/static/ui.js"])
        assert all("defer" in s for s in locais), (rota, locais)
