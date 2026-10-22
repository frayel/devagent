"""PR sem trabalho na branch fecha na hora, sem cobrar o agente (ADR 018).

Caso de 22/10: o #402 dizia entregar uma spec e só trazia o relatório da
execução. A cobrança abriu uma sessão filha, que criou o #403 sem nenhum
arquivo. Os dois ficaram horas abertos travando o ciclo.
"""

from __future__ import annotations

from typing import Any

import pytest

from devagent import guardiao_prs


def test_pr_vazio_e_irrecuperavel() -> None:
    assert "nenhum arquivo" in guardiao_prs.motivo_irrecuperavel([])


def test_pr_so_de_registro_e_irrecuperavel() -> None:
    motivo = guardiao_prs.motivo_irrecuperavel(["docs/runs/2026-10-21-2339.md"])
    assert "perdeu o trabalho" in motivo


def test_registro_que_fecha_issue_nao_e_irrecuperavel() -> None:
    assert (
        guardiao_prs.motivo_irrecuperavel(
            ["docs/runs/x.md", ".jules/sentinel.md"], "Closes #12"
        )
        == ""
    )


def test_pr_com_codigo_nao_e_irrecuperavel() -> None:
    assert guardiao_prs.motivo_irrecuperavel(["app/x.py", "docs/runs/x.md"]) == ""


def test_sem_leitura_dos_arquivos_nao_fecha() -> None:
    assert guardiao_prs.motivo_irrecuperavel(None) == ""


def test_ci_falhou_fecha_sem_cobrar(monkeypatch: pytest.MonkeyPatch) -> None:
    pr = {
        "number": 402,
        "title": "Implementa spec 075",
        "headRefName": "jules-1",
        "body": "",
        "url": "u",
    }
    chamadas: dict[str, Any] = {}
    monkeypatch.setattr(guardiao_prs, "prs_do_agente", lambda: [pr])
    monkeypatch.setattr(guardiao_prs, "sh", lambda *a, **k: "log")
    monkeypatch.setattr(guardiao_prs, "arquivos_do_pr", lambda n: ["docs/runs/a.md"])
    monkeypatch.setattr(
        guardiao_prs, "comentar", lambda n, c: chamadas.setdefault("comentou", c)
    )

    def fechar(
        p: dict[str, Any], motivo: str, detalhe: str = "", registrar: bool = False
    ) -> None:
        chamadas["fechou"] = (p["number"], registrar)

    monkeypatch.setattr(guardiao_prs, "fechar", fechar)
    guardiao_prs.ci_falhou("jules-1", "1")
    assert chamadas["fechou"] == (402, True)
    assert "comentou" not in chamadas
