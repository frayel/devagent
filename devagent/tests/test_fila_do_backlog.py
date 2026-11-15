"""Regra 10 do conferir_pr: a Fila do backlog tem teto e a ideia que vira spec sai dela."""

from __future__ import annotations

from pathlib import Path

import pytest

from devagent.conferir_pr import conferir, itens_da_fila
from devagent.tests.test_conferir_pr import escrever, git, repo  # noqa: F401

TITULO = "spec: 170 · Radar novo"


def backlog(*itens: str) -> str:
    linhas = "".join(
        f"| {i} | Experiência | {nome} | Pergunta | P |\n"
        for i, nome in enumerate(itens, 1)
    )
    return (
        "# Backlog\n\n## Correções (prioridade sobre qualquer feature)\n\n"
        "## Fila\n\n| # | Gaveta | Ideia | Pergunta e evidência | Esforço |\n"
        "|---|---|---|---|---|\n" + linhas + "\n## Reserva\n\n- outra coisa\n"
    )


def spec_nova(origem: str | None) -> str:
    campo = f"origem: {origem}\n" if origem is not None else ""
    return f"---\nid: 170\ntitulo: Radar novo\nstatus: ready\ngaveta: experiência\n{campo}---\n\nTexto.\n"


@pytest.fixture
def com_fila(repo: Path) -> Path:  # noqa: F811
    escrever(repo, {"docs/BACKLOG.md": backlog("Radar novo", "Modo `TV`")})
    git(repo, "commit", "-qam", "fila")
    git(repo, "branch", "-f", "base", "HEAD")
    return repo


def falhas(raiz: Path) -> list[str]:
    return conferir(raiz, "base", titulo=TITULO, corpo="").falhas


def test_le_os_nomes_da_coluna_ideia() -> None:
    assert [
        n for n, _ in itens_da_fila(backlog("Radar novo", "Modo `TV`"), "Fila")
    ] == [
        "radar novo",
        "modo tv",
    ]


def test_spec_que_tira_o_item_da_fila_passa(com_fila: Path) -> None:
    escrever(
        com_fila,
        {
            "docs/specs/170-radar.md": spec_nova("Radar novo"),
            "docs/BACKLOG.md": backlog("Modo `TV`"),
        },
    )
    assert falhas(com_fila) == []


def test_item_que_fica_na_fila_reprova(com_fila: Path) -> None:
    escrever(com_fila, {"docs/specs/170-radar.md": spec_nova("Radar novo")})
    assert any("continua na Fila" in f for f in falhas(com_fila))


def test_item_que_fica_citando_a_spec_passa(com_fila: Path) -> None:
    escrever(
        com_fila,
        {
            "docs/specs/170-radar.md": spec_nova("radar  NOVO"),
            "docs/BACKLOG.md": backlog("Radar novo", "Modo `TV`").replace(
                "| Pergunta | P |", "| Resto da visão depois da spec 170 | P |", 1
            ),
        },
    )
    assert falhas(com_fila) == []


def test_spec_sem_origem_reprova(com_fila: Path) -> None:
    escrever(com_fila, {"docs/specs/170-radar.md": spec_nova(None)})
    assert any("não declara `origem:`" in f for f in falhas(com_fila))


def test_origem_que_nao_esta_na_fila_reprova(com_fila: Path) -> None:
    escrever(com_fila, {"docs/specs/170-radar.md": spec_nova("Radar inventado")})
    assert any("não é o nome de nenhum item" in f for f in falhas(com_fila))


@pytest.mark.parametrize("origem", ["nova", "issue #42"])
def test_origem_livre_passa(com_fila: Path, origem: str) -> None:
    escrever(com_fila, {"docs/specs/170-radar.md": spec_nova(origem)})
    assert falhas(com_fila) == []


def test_fila_acima_do_teto_reprova(com_fila: Path) -> None:
    escrever(com_fila, {"docs/BACKLOG.md": backlog(*[f"Ideia {i}" for i in range(26)])})
    assert any("o teto é 25" in f for f in conferir(com_fila, "base").falhas)


def test_spec_antiga_e_pr_de_desenvolvimento_ficam_fora(com_fila: Path) -> None:
    escrever(
        com_fila, {"docs/specs/150-velha.md": spec_nova(None).replace("170", "150")}
    )
    assert not any("origem" in f for f in falhas(com_fila))
    escrever(com_fila, {"docs/specs/170-radar.md": spec_nova(None)})
    resultado = conferir(com_fila, "base", titulo="feat: algo", corpo="").falhas
    assert not any("origem" in f for f in resultado)
