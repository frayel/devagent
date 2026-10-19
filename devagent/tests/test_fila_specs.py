"""A fila de specs ready e o prompt do desenvolvedor (ADR 015)."""

from __future__ import annotations

from pathlib import Path

import pytest

from devagent import fila_specs
from devagent.adaptadores import jules


def _spec(pasta: Path, nome: str, status: str) -> None:
    (pasta / nome).write_text(f"---\nid: 1\nstatus: {status}\n---\n", encoding="utf-8")


@pytest.fixture
def raiz(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    pasta = tmp_path / "docs" / "specs"
    pasta.mkdir(parents=True)
    _spec(pasta, "080-poda.md", "ready")
    _spec(pasta, "068b-regras.md", "ready")
    _spec(pasta, "068a-rota.md", "done")
    _spec(pasta, "069-confianca.md", "ready")
    _spec(pasta, "068-original.md", "draft")
    _spec(pasta, "100-futura.md", "ready")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_ordem_natural_e_so_ready(raiz: Path) -> None:
    nomes = [p.name for p in fila_specs.specs_prontas(raiz)]
    assert nomes == [
        "068b-regras.md",
        "069-confianca.md",
        "080-poda.md",
        "100-futura.md",
    ]


def test_instrucao_aponta_a_menor(raiz: Path) -> None:
    texto = fila_specs.instrucao(fila_specs.specs_prontas(raiz), raiz)
    assert "docs/specs/068b-regras.md" in texto
    assert "não escreva spec nova" in texto


def test_fila_vazia_sem_instrucao(tmp_path: Path) -> None:
    assert fila_specs.specs_prontas(tmp_path) == []
    assert fila_specs.instrucao([]) == ""


def test_prompt_do_desenvolvedor_traz_a_proxima_spec(raiz: Path) -> None:
    prompt = jules.prompt_de("desenvolvedor")
    assert prompt.startswith(jules.PERSONAS["desenvolvedor"]["prompt"])
    assert "068b-regras.md" in prompt


def test_prompt_sem_fila_e_o_fixo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    assert jules.prompt_de("desenvolvedor") == jules.PERSONAS["desenvolvedor"]["prompt"]


def test_auditor_nao_recebe_a_fila(raiz: Path) -> None:
    assert jules.prompt_de("auditor") == jules.PERSONAS["auditor"]["prompt"]
