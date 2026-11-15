"""Retomada depois de ambiente reiniciado (ADR 009): a cobrança do guardião."""

from __future__ import annotations

import pytest

from devagent import guardiao_prs


def test_cobranca_do_guardiao_traz_a_retomada(monkeypatch: pytest.MonkeyPatch) -> None:
    pr = {"number": 7, "headRefName": "feat/026-x", "url": "u", "title": "t"}
    comentarios: list[str] = []
    monkeypatch.setattr(guardiao_prs, "prs_do_agente", lambda: [pr])
    monkeypatch.setattr(guardiao_prs, "comentarios", lambda n: [])
    monkeypatch.setattr(guardiao_prs, "sh", lambda *a, **k: "log")
    monkeypatch.setattr(
        guardiao_prs, "comentar", lambda n, corpo: comentarios.append(corpo)
    )
    guardiao_prs.ci_falhou("feat/026-x", "1")
    assert comentarios
    assert "git checkout -B feat/026-x origin/feat/026-x" in comentarios[0]
    assert "não recomece" in comentarios[0]
