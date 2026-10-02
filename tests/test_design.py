"""Guarda do guia visual (docs/DESIGN.md).

Verifica o que é verificável sem olhar a tela: tokens num único lugar, nenhum
estilo inline, nenhuma cor solta e a página usando o tema escuro.

Enquanto a spec 008 (redesign) não for implementada, estes testes falham e
estão marcados como xfail ESTRITO. Quando a interface passar a cumprir o
guia, os testes passam, o xfail estrito acusa XPASS e o CI falha de propósito:
a spec 008 manda remover o marcador `pytestmark` abaixo no mesmo PR. Depois
disso, estes testes protegem o guia para sempre.
"""

import re
from pathlib import Path

from fastapi.testclient import TestClient

RAIZ = Path(__file__).resolve().parent.parent
TEMPLATES = RAIZ / "app" / "templates"
STATIC = RAIZ / "app" / "static"
TEMA = STATIC / "tema.css"

TOKENS = [
    "--fundo",
    "--superficie",
    "--superficie-2",
    "--borda",
    "--texto",
    "--texto-2",
    "--texto-3",
    "--destaque",
    "--alta",
    "--baixa",
    "--alerta",
    "--fs-meta",
    "--fs-base",
    "--fs-titulo",
    "--fs-kpi",
    "--fs-hero",
    "--e1",
    "--e2",
    "--e3",
    "--e4",
    "--e5",
    "--raio",
]
COR_SOLTA = re.compile(r"#[0-9a-fA-F]{3,8}\b|\brgba?\(")


def _arquivos_de_interface() -> list[Path]:
    arquivos = list(TEMPLATES.glob("**/*.html"))
    if STATIC.exists():
        arquivos += [p for p in STATIC.glob("**/*") if p.suffix in {".css", ".js"}]
    return [p for p in arquivos if p != TEMA]


def test_tema_declara_todos_os_tokens_e_e_escuro():
    css = TEMA.read_text(encoding="utf-8")
    faltando = [t for t in TOKENS if not re.search(re.escape(t) + r"\s*:", css)]
    assert not faltando, f"tokens ausentes em tema.css: {faltando}"
    assert re.search(r"color-scheme\s*:\s*dark", css)


def test_templates_sem_estilo_inline():
    com_estilo = [
        p.name for p in TEMPLATES.glob("**/*.html") if "style=" in p.read_text("utf-8")
    ]
    assert not com_estilo


def test_cores_so_nos_tokens():
    soltas = {
        str(p.relative_to(RAIZ)): COR_SOLTA.findall(p.read_text("utf-8"))
        for p in _arquivos_de_interface()
    }
    soltas = {k: v for k, v in soltas.items() if v}
    assert not soltas, f"cores fora de tema.css: {soltas}"


def test_graficos_passam_pelo_tema():
    assert (STATIC / "graficos.js").exists()


def test_pagina_usa_tema_grade_e_componentes():
    from app.main import app

    html = TestClient(app).get("/").text
    assert "/static/tema.css" in html
    assert 'class="grade"' in html
    assert "style=" not in html
    assert (TEMPLATES / "componentes.html").exists()
