"""Aceite executável: regra 7 do conferir_pr e o helper devagent.aceite (ADR 018)."""

from __future__ import annotations

from pathlib import Path

import pytest

from devagent import aceite, conferir_pr
from devagent.tests.test_conferir_pr import escrever, fechar, repo  # noqa: F401


def com_aceite(numero: int, status: str, aceite_: str) -> str:
    return (
        f"---\nid: {numero:03d}\ntitulo: Spec {numero}\nstatus: {status}\n"
        f"aceite: {aceite_}\n---\n\nTexto.\n"
    )


def test_aceite_listado_e_presente_passa(repo: Path) -> None:  # noqa: F811
    fechar(repo)
    escrever(
        repo,
        {
            "docs/specs/001-a.md": com_aceite(1, "done", "tests/test_aceite_001.py"),
            "tests/test_aceite_001.py": "def test_x():\n    pass\n",
        },
    )
    assert conferir_pr.conferir(repo, "base").falhas == []


def test_aceite_listado_e_ausente_reprova(repo: Path) -> None:  # noqa: F811
    fechar(repo)
    escrever(
        repo,
        {"docs/specs/001-a.md": com_aceite(1, "done", "tests/test_aceite_001.py")},
    )
    falhas = conferir_pr.conferir(repo, "base").falhas
    assert any("test_aceite_001.py" in f and "não existe" in f for f in falhas)


def test_aceite_vale_para_spec_movida_para_done(repo: Path) -> None:  # noqa: F811
    fechar(repo)
    (repo / "docs/specs/001-a.md").unlink()
    escrever(
        repo,
        {"docs/specs/done/001-a.md": com_aceite(1, "done", "tests/test_falta.py")},
    )
    falhas = conferir_pr.conferir(repo, "base").falhas
    assert any("test_falta.py" in f for f in falhas)


def test_aceite_obrigatorio_a_partir_do_limite(
    repo: Path,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(
        conferir_pr.CONFIG, "disciplina", {"aceite_obrigatorio_desde": "002"}
    )
    fechar(repo, numero=2)
    falhas = conferir_pr.conferir(repo, "base").falhas
    assert any("002-b.md" in f and "aceite" in f for f in falhas)

    # Abaixo do limite, a spec antiga fecha sem o campo.
    escrever(repo, {"docs/specs/002-b.md": conferir_pr_spec(2, "ready")})
    fechar(repo, numero=1)
    assert conferir_pr.conferir(repo, "base").falhas == []


def conferir_pr_spec(numero: int, status: str) -> str:
    return f"---\nid: {numero:03d}\ntitulo: Spec {numero}\nstatus: {status}\n---\n"


def test_status_da_spec_acha_em_subpasta(tmp_path: Path) -> None:
    escrever(
        tmp_path,
        {
            "docs/specs/075a-x.md": conferir_pr_spec(1, "ready").replace(
                "id: 001", "id: 075a"
            ),
            "docs/specs/done/074-y.md": conferir_pr_spec(74, "done"),
        },
    )
    assert aceite.status_da_spec("075a", tmp_path) == "ready"
    assert aceite.status_da_spec("74", tmp_path) == "done"
    assert aceite.status_da_spec("075", tmp_path) is None


def test_exigir_spec_done_pula_enquanto_nao_fecha(tmp_path: Path) -> None:
    escrever(tmp_path, {"docs/specs/005-z.md": conferir_pr_spec(5, "ready")})
    with pytest.raises(pytest.skip.Exception):
        aceite.exigir_spec_done("005", tmp_path)
    escrever(tmp_path, {"docs/specs/005-z.md": conferir_pr_spec(5, "done")})
    aceite.exigir_spec_done("005", tmp_path)
