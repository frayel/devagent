"""Repositório público: só o dono, colaboradores e bots instalados dirigem o agente.

Revisão de segurança de 19/11: issue de estranho virava `prioridade`, o
marcador de raia num PR de fork o fazia passar por PR do agente, e o
automerge mesclava PR de fork com CI verde.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from devagent import estado_github
from devagent.confianca import autor_confiavel


@pytest.mark.parametrize(
    "item, confia",
    [
        ({"author_association": "OWNER"}, True),
        ({"author_association": "COLLABORATOR"}, True),
        ({"author_association": "MEMBER"}, True),
        ({"authorAssociation": "OWNER"}, True),
        ({"author_association": "NONE", "user": {"type": "User"}}, False),
        ({"author_association": "CONTRIBUTOR", "user": {"type": "User"}}, False),
        ({"author_association": "FIRST_TIME_CONTRIBUTOR"}, False),
        ({"author_association": "NONE", "user": {"type": "Bot"}}, True),
        ({"author": {"login": "app/github-actions", "is_bot": True}}, True),
        ({}, False),
    ],
)
def test_autor_confiavel(item: dict[str, Any], confia: bool) -> None:
    assert autor_confiavel(item) is confia


def _pr(numero: int, associacao: str, corpo: str = "") -> dict[str, Any]:
    return {
        "number": numero,
        "title": "feat: algo",
        "body": corpo,
        "head": {"ref": f"b{numero}", "sha": "abc"},
        "labels": [],
        "created_at": "2026-11-19T00:00:00Z",
        "user": {"login": f"u{numero}", "type": "User"},
        "author_association": associacao,
    }


def _issue(numero: int, associacao: str) -> dict[str, Any]:
    return {
        "number": numero,
        "title": f"issue {numero}",
        "labels": [],
        "created_at": "2026-11-19T00:00:00Z",
        "user": {"login": f"u{numero}", "type": "User"},
        "author_association": associacao,
    }


def test_estado_ignora_issue_e_pr_de_estranho(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    marcador = "<!-- devagent:raia:desenvolvimento -->"
    respostas = {
        "pulls?state=open": [_pr(1, "OWNER", marcador), _pr(2, "NONE", marcador)],
        "issues?state=open": [_issue(3, "OWNER"), _issue(4, "NONE")],
    }

    def get(caminho: str) -> Any:
        for chave, valor in respostas.items():
            if chave in caminho:
                return valor
        if "/check-runs" in caminho:
            return {"check_runs": []}
        return {"mergeable_state": "clean", "comments": 0, "review_comments": 0}

    monkeypatch.setattr(estado_github, "_get", get)
    monkeypatch.setattr(estado_github, "_repo", lambda: "dono/repo")
    estado = estado_github.coletar()
    assert [p["numero"] for p in estado["prs"]] == [1]
    assert estado["prs"][0]["do_agente"] is True
    assert [i["numero"] for i in estado["issues"]] == [3]


def test_marcador_de_raia_nao_basta_sem_autor_confiavel() -> None:
    pr = _pr(2, "NONE", "<!-- devagent:raia:desenvolvimento -->")
    assert estado_github.eh_do_agente(pr) is False


WORKFLOWS = Path(__file__).resolve().parents[2] / ".github" / "workflows"


def test_automerge_e_guardiao_ignoram_fork() -> None:
    condicao = (
        "github.event.workflow_run.head_repository.full_name == github.repository"
    )
    assert condicao in (WORKFLOWS / "automerge.yml").read_text(encoding="utf-8")
    assert condicao in (WORKFLOWS / "pr-guardiao.yml").read_text(encoding="utf-8")
    assert "isCrossRepository" in (WORKFLOWS / "automerge.yml").read_text(
        encoding="utf-8"
    )


def test_workflow_nao_interpola_texto_do_autor_no_script() -> None:
    """Nome de branch, título e corpo vêm do autor: só por variável de ambiente."""
    perigosos = (
        "workflow_run.head_branch",
        "workflow_run.display_title",
        "pull_request.title",
        "pull_request.body",
        "pull_request.head.ref",
        "issue.title",
        "issue.body",
        "comment.body",
    )
    for arquivo in WORKFLOWS.glob("*.yml"):
        for numero, linha in enumerate(
            arquivo.read_text(encoding="utf-8").splitlines()
        ):
            if "${{" not in linha or not any(p in linha for p in perigosos):
                continue
            chave = linha.strip().split(":", 1)[0]
            assert chave.isupper(), f"{arquivo.name}:{numero + 1} interpola {linha!r}"
