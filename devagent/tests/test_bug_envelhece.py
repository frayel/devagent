"""ADR 030: bug aberto há mais de 24 h ganha `prioridade`.

Em 28/10 a #557 e a #570 (achados de severidade baixa) esperavam atrás de 12
specs: o Passo 6 só roda com a fila vazia.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from devagent import guardiao_prs

AGORA = datetime(2026, 10, 29, 12, 0, tzinfo=timezone.utc)


def _issue(numero: int, criada: str, *labels: str) -> dict[str, Any]:
    return {
        "number": numero,
        "createdAt": criada,
        "labels": [{"name": nome} for nome in labels],
    }


def test_bug_antigo_ganha_prioridade() -> None:
    issues = [
        _issue(557, "2026-10-27T21:35:06Z", "bug", "verificacao"),
        _issue(570, "2026-10-28T08:20:40Z", "bug", "verificacao"),
    ]
    assert guardiao_prs.bugs_para_priorizar(issues, AGORA) == [557, 570]


def test_bug_recente_espera() -> None:
    issues = [_issue(600, "2026-10-29T01:00:00Z", "bug")]
    assert guardiao_prs.bugs_para_priorizar(issues, AGORA) == []


def test_ja_priorizado_ou_bloqueado_fica_de_fora() -> None:
    issues = [
        _issue(1, "2026-10-20T00:00:00Z", "bug", "prioridade"),
        _issue(2, "2026-10-20T00:00:00Z", "bug", "bloqueado"),
        _issue(3, "2026-10-20T00:00:00Z", "enhancement"),
    ]
    assert guardiao_prs.bugs_para_priorizar(issues, AGORA) == []


def test_priorizar_aplica_o_label_e_explica(monkeypatch: pytest.MonkeyPatch) -> None:
    comandos: list[tuple[str, ...]] = []
    monkeypatch.setattr(guardiao_prs, "agora", lambda: AGORA)
    monkeypatch.setattr(
        guardiao_prs,
        "gh_json",
        lambda *a: [_issue(557, "2026-10-27T21:35:06Z", "bug")],
    )
    monkeypatch.setattr(guardiao_prs, "sh", lambda *a, **k: comandos.append(a) or "")
    guardiao_prs.priorizar_bugs_antigos()
    assert ("gh", "issue", "edit", "557", "--add-label", "prioridade") in comandos
    assert any(c[:4] == ("gh", "issue", "comment", "557") for c in comandos)
