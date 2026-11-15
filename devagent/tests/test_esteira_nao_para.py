"""ADR 025: a esteira não para e não gasta cota à toa.

Casos de 28/10: o #586 e o #565 (verificação sem achado novo) seguraram a
raia de verificação ~4 h cada um.
"""

from __future__ import annotations

from typing import Any

import pytest

from devagent import guardiao_prs

# --- Guardião: verificação sem achado fecha na hora ------------------------

VERIFICACAO = {
    "number": 586,
    "title": "verificação: 2026-10-28 · 0 achados",
    "headRefName": "verificacao-1",
    "body": "",
    "url": "u",
}


def test_verificacao_sem_achado_novo() -> None:
    assert guardiao_prs.sem_achado_de_verificacao(VERIFICACAO, [])


def test_verificacao_com_achado_novo_segue() -> None:
    novos = ["docs/verificacao/achados/2026-10-29-x.md"]
    assert not guardiao_prs.sem_achado_de_verificacao(VERIFICACAO, novos)


def test_verificacao_sem_leitura_dos_arquivos_nao_fecha() -> None:
    assert not guardiao_prs.sem_achado_de_verificacao(VERIFICACAO, None)


def test_outra_raia_nao_e_verificacao_sem_achado() -> None:
    pr = {"title": "feat: spec 124", "body": ""}
    assert not guardiao_prs.sem_achado_de_verificacao(pr, [])


def test_ci_falhou_de_verificacao_sem_achado_fecha_sem_issue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chamadas: list[Any] = []
    monkeypatch.setattr(guardiao_prs, "prs_do_agente", lambda: [VERIFICACAO])
    monkeypatch.setattr(
        guardiao_prs,
        "arquivos_do_pr",
        lambda n: ["docs/verificacao/diario.md", "docs/verificacao/achados/velho.md"],
    )
    monkeypatch.setattr(guardiao_prs, "achados_novos_do_pr", lambda n: [])
    monkeypatch.setattr(guardiao_prs, "sh", lambda *a, **k: chamadas.append(a) or "log")
    monkeypatch.setattr(
        guardiao_prs, "comentar", lambda n, c: chamadas.append(("comentar", n, c))
    )

    def fechar(*a: Any, **k: Any) -> None:
        raise AssertionError("não deveria abrir tentativa-falhou")

    monkeypatch.setattr(guardiao_prs, "fechar", fechar)
    guardiao_prs.ci_falhou("verificacao-1", "1")
    comentarios = [c for c in chamadas if c[0] == "comentar"]
    assert comentarios and "ADR 025" in comentarios[0][2]
    assert "@antigravity" not in comentarios[0][2]
    assert any(a[:3] == ("gh", "pr", "close") for a in chamadas)
