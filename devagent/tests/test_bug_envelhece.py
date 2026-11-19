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


def _rest(
    numero: int, criada: str, *labels: str, associacao: str = "OWNER"
) -> dict[str, Any]:
    """Issue como a API REST devolve (o `gh api` do guardião)."""
    return {
        "number": numero,
        "created_at": criada,
        "labels": [{"name": nome} for nome in labels],
        "author_association": associacao,
        "user": {"login": "x", "type": "User"},
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
        _issue(4, "2026-10-20T00:00:00Z", "prioridade"),
        _issue(5, "2026-10-20T00:00:00Z", "bloqueado"),
    ]
    assert guardiao_prs.bugs_para_priorizar(issues, AGORA) == []


def test_issue_sem_label_envelhece_como_bug() -> None:
    """A #902 (16/11) foi aberta sem label e nunca entrou na varredura."""
    issues = [
        _issue(902, "2026-10-28T08:32:46Z"),
        _issue(903, "2026-10-29T06:00:00Z"),
    ]
    assert guardiao_prs.bugs_para_priorizar(issues, AGORA) == [902]


def test_priorizar_aplica_o_label_e_explica(monkeypatch: pytest.MonkeyPatch) -> None:
    comandos: list[tuple[str, ...]] = []
    consultas: list[tuple[str, ...]] = []
    monkeypatch.setattr(guardiao_prs, "agora", lambda: AGORA)
    monkeypatch.setattr(
        guardiao_prs,
        "gh_json",
        lambda *a: (
            consultas.append(a)
            or [
                _rest(557, "2026-10-27T21:35:06Z", "bug"),
                _rest(902, "2026-10-27T08:32:46Z"),
                _rest(908, "2026-10-27T12:51:00Z", "enhancement"),
            ]
        ),
    )
    monkeypatch.setattr(guardiao_prs, "sh", lambda *a, **k: comandos.append(a) or "")
    guardiao_prs.priorizar_bugs_antigos()
    # A consulta não filtra por `bug`: senão a issue sem label nem chega.
    assert all("--label" not in c for c in consultas)
    for numero in ("557", "902"):
        assert ("gh", "issue", "edit", numero, "--add-label", "prioridade") in comandos
        assert any(c[:4] == ("gh", "issue", "comment", numero) for c in comandos)
    assert not any("908" in c for c in comandos)


# Repositório público (revisão de 19/11): issue de estranho sem label viraria
# `prioridade` em 24 h, e o agente a implementaria.
def test_issue_de_estranho_nao_ganha_prioridade(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    comandos: list[tuple[str, ...]] = []
    monkeypatch.setattr(guardiao_prs, "agora", lambda: AGORA)
    monkeypatch.setattr(
        guardiao_prs,
        "gh_json",
        lambda *a: [
            _rest(901, "2026-10-27T08:00:00Z", associacao="NONE"),
            _rest(902, "2026-10-27T08:00:00Z", "bug", associacao="CONTRIBUTOR"),
            _rest(903, "2026-10-27T08:00:00Z", associacao="COLLABORATOR"),
            {**_rest(904, "2026-10-27T08:00:00Z"), "pull_request": {}},
        ],
    )
    monkeypatch.setattr(guardiao_prs, "sh", lambda *a, **k: comandos.append(a) or "")
    guardiao_prs.priorizar_bugs_antigos()
    editadas = [c[3] for c in comandos if c[:3] == ("gh", "issue", "edit")]
    assert editadas == ["903"]
