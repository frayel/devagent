"""Tentativa que nenhum passo do ciclo lê é fechada pelo guardião (ADR 020).

Casos de 23/10: a #416 registrou a falha do #415 (spec 076b), entregue depois
no #414 sem `Closes`; a #427 registrou um PR vazio do Sentinel, sem spec.
"""

from __future__ import annotations

from typing import Any

import pytest

from devagent import guardiao_prs
from devagent.auditoria import achados_para_issues


def test_spec_citada_por_extenso_caminho_e_marcador() -> None:
    texto = "feat: x (spec 077c)\n<!-- spec: 76b -->\nfecha #75, ano 2026"
    arquivos = ["docs/specs/076b-lote.md", "docs/specs/080-poda.md", "app/a.py"]
    assert guardiao_prs.specs_citadas(texto, arquivos) == ["077c", "76b", "080"]


def test_titulo_sem_numero_nao_cita_spec() -> None:
    titulo = "implement(spec): migrar 7 paineis (lote 3 parte b)"
    assert guardiao_prs.specs_citadas(titulo) == []


def test_sem_spec_e_orfa() -> None:
    assert "não cita spec" in guardiao_prs.motivo_tentativa_orfa([], {})


def test_spec_done_e_orfa() -> None:
    motivo = guardiao_prs.motivo_tentativa_orfa(["076b"], {"76b": "done"})
    assert "spec 076b" in motivo


def test_spec_ainda_ready_nao_e_orfa() -> None:
    status = {"76b": "done", "77d": "ready"}
    assert guardiao_prs.motivo_tentativa_orfa(["076b", "077d"], status) == ""


def test_spec_desconhecida_nao_e_orfa() -> None:
    assert guardiao_prs.motivo_tentativa_orfa(["999"], {}) == ""


def _issue(numero: int, titulo: str, corpo: str, *labels: str) -> dict[str, Any]:
    return {
        "number": numero,
        "title": titulo,
        "body": corpo,
        "labels": [{"name": n} for n in ("tentativa-falhou", *labels)],
    }


def test_varredura_fecha_so_as_orfas(monkeypatch: pytest.MonkeyPatch) -> None:
    issues = [
        _issue(416, "Tentativa fechada: lote 3 parte b", "fechou .../pull/415 (x)"),
        _issue(427, "Tentativa fechada: Sentinel", "fechou .../pull/426"),
        _issue(430, "Tentativa fechada: spec 077d", "<!-- spec: 077d -->"),
        _issue(431, "Tentativa fechada: Sentinel", "sem spec", "bloqueado"),
    ]
    arquivos = {415: ["docs/specs/076b-lote.md", "app/db.py"], 426: []}
    fechadas: list[str] = []

    def sh(*a: str, check: bool = True) -> str:
        if a[:3] == ("gh", "issue", "close"):
            fechadas.append(a[3])
        return ""

    monkeypatch.setattr(guardiao_prs, "gh_json", lambda *a: issues)
    monkeypatch.setattr(guardiao_prs, "sh", sh)
    monkeypatch.setattr(guardiao_prs, "arquivos_do_pr", lambda n: arquivos.get(n))
    monkeypatch.setattr(
        guardiao_prs, "status_das_specs", lambda: {"76b": "done", "77d": "ready"}
    )
    guardiao_prs.fechar_tentativas_orfas()
    assert fechadas == ["416", "427"]


def test_issue_nova_registra_a_spec(monkeypatch: pytest.MonkeyPatch) -> None:
    pr = {
        "number": 415,
        "title": "implement(spec): lote 3 parte b",
        "headRefName": "jules-x",
        "body": "",
        "url": "u",
    }
    corpos: list[str] = []

    def sh(*a: str, check: bool = True) -> str:
        if a[:3] == ("gh", "issue", "create"):
            corpos.append(a[a.index("--body") + 1])
        return ""

    monkeypatch.setattr(guardiao_prs, "sh", sh)
    monkeypatch.setattr(guardiao_prs, "comentar", lambda n, c: None)
    monkeypatch.setattr(
        guardiao_prs, "arquivos_do_pr", lambda n: ["docs/specs/076b-lote.md"]
    )
    guardiao_prs.fechar(pr, "conflito grande", registrar=True)
    assert "spec 076b" in corpos[0]
    assert "<!-- spec: 076b -->" in corpos[0]


def test_achado_medio_entra_com_prioridade(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    for nome, sev in (("a1.md", "media"), ("a2.md", "alta")):
        (tmp_path / nome).write_text(
            f"---\nid: {nome}\nseveridade: {sev}\n---\n# Achado {nome}\n",
            encoding="utf-8",
        )
    monkeypatch.setattr(achados_para_issues, "PASTA", tmp_path)
    achados_para_issues.main(["--dry-run"])
    saida = capsys.readouterr().out
    linha_media = next(ln for ln in saida.splitlines() if "a1.md" in ln)
    linha_alta = next(ln for ln in saida.splitlines() if "a2.md" in ln)
    assert "'prioridade'" in linha_media and "producao-incorreta" not in linha_media
    assert "'producao-incorreta'" in linha_alta and "prioridade" not in linha_alta
