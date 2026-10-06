"""Nenhum painel pode mostrar marcação HTML como texto (ex.: "<span>+591%</span>")."""

import importlib.util
from pathlib import Path

from fastapi.testclient import TestClient

import app.database as db
from app.main import app


def _semear_demonstracao() -> None:
    caminho = Path(__file__).resolve().parent.parent / "scripts" / "telas.py"
    spec = importlib.util.spec_from_file_location("telas_demo", caminho)
    assert spec and spec.loader
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    modulo._semear(db.DB_PATH)


def test_pagina_nao_mostra_tags_escapadas():
    _semear_demonstracao()
    html = TestClient(app).get("/").text
    assert "&lt;span" not in html
    assert "&lt;/span" not in html
