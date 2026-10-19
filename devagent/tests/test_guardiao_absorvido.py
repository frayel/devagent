"""PR cujo conteúdo já chegou à main não vira issue `tentativa-falhou` (ADR 014).

Reproduz o caso de 19/10: o #344 carregava o trabalho do #343 (já mesclado em
squash) mais um relatório de execução, e entrou em conflito porque o #345
mexeu de novo nos mesmos arquivos.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest

from devagent import guardiao_prs


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    ).stdout


def escrever(repo: Path, caminho: str, texto: str) -> None:
    arquivo = repo / caminho
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    arquivo.write_text(texto, encoding="utf-8")


def commit(repo: Path, msg: str) -> None:
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", msg)


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    git(tmp_path, "init", "-q", "-b", "main")
    git(tmp_path, "config", "user.email", "t@t")
    git(tmp_path, "config", "user.name", "t")
    escrever(tmp_path, "nucleo.py", "".join(f"linha {i}\n" for i in range(30)))
    commit(tmp_path, "base")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def trabalho_do_pr(repo: Path) -> None:
    """O que o #343 fazia: mexe no núcleo e cria uma decisão."""
    texto = (repo / "nucleo.py").read_text().replace("linha 10\n", "linha 10 nova\n")
    escrever(repo, "nucleo.py", texto)
    escrever(repo, "decisoes/012.md", "decisão\n")


def cenario_19_10(repo: Path) -> None:
    git(repo, "checkout", "-q", "-b", "pr")
    trabalho_do_pr(repo)
    commit(repo, "trabalho")
    escrever(repo, "docs/runs/2026-10-19-0237.md", "relatório\n")
    commit(repo, "relatório")
    git(repo, "checkout", "-q", "main")
    trabalho_do_pr(repo)  # o #343 entra por squash
    commit(repo, "squash do 343")
    texto = (
        (repo / "nucleo.py")
        .read_text()
        .replace("linha 10 nova\n", "linha 10 nova e refeita\n")
    )
    escrever(repo, "nucleo.py", texto)  # o #345 mexe no mesmo trecho
    commit(repo, "345")


def test_so_sobra_o_relatorio_quando_o_trabalho_ja_entrou(repo: Path):
    cenario_19_10(repo)
    assert guardiao_prs.pendentes_fora_da_main("pr", "main") == [
        "docs/runs/2026-10-19-0237.md"
    ]


def test_trabalho_que_nunca_entrou_fica_pendente(repo: Path):
    git(repo, "checkout", "-q", "-b", "pr")
    trabalho_do_pr(repo)
    commit(repo, "trabalho")
    git(repo, "checkout", "-q", "main")
    escrever(repo, "outro.md", "x\n")
    commit(repo, "outra coisa")
    assert guardiao_prs.pendentes_fora_da_main("pr", "main") == [
        "decisoes/012.md",
        "nucleo.py",
    ]


def test_mudanca_parcial_nao_conta_como_absorvida(repo: Path):
    git(repo, "checkout", "-q", "-b", "pr")
    trabalho_do_pr(repo)
    commit(repo, "trabalho")
    git(repo, "checkout", "-q", "main")
    escrever(repo, "decisoes/012.md", "decisão\n")  # só metade entrou
    commit(repo, "metade")
    assert guardiao_prs.pendentes_fora_da_main("pr", "main") == ["nucleo.py"]


@pytest.fixture
def acoes(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, ...]]:
    registro: list[tuple[str, ...]] = []

    def sh(*cmd: str, check: bool = True) -> str:
        registro.append(cmd)
        return ""

    monkeypatch.setattr(guardiao_prs, "sh", sh)
    monkeypatch.setattr(
        guardiao_prs, "comentar", lambda n, c: registro.append(("comentar", c))
    )
    return registro


PR: dict[str, Any] = {
    "number": 344,
    "title": "Registro da execução",
    "headRefName": "pr",
    "url": "https://github.com/dono/repo/pull/344",
}


def abriu_issue(acoes: list[tuple[str, ...]]) -> bool:
    return any(a[:3] == ("gh", "issue", "create") for a in acoes)


def test_fechar_absorvido_nao_abre_issue(acoes, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(guardiao_prs, "absorvido_pela_main", lambda b: True)
    guardiao_prs.fechar(PR, "conflito grande com a `main`.")
    assert ("gh", "pr", "close", "344", "--delete-branch") in acoes
    assert not abriu_issue(acoes)


def test_fechar_com_trabalho_pendente_abre_issue(
    acoes, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(guardiao_prs, "absorvido_pela_main", lambda b: False)
    guardiao_prs.fechar(PR, "conflito grande com a `main`.")
    assert abriu_issue(acoes)


def test_falha_na_comparacao_cai_no_comportamento_antigo(
    monkeypatch: pytest.MonkeyPatch,
):
    def falha(*cmd: str, check: bool = True) -> str:
        raise RuntimeError("shallow")

    monkeypatch.setattr(guardiao_prs, "sh", falha)
    assert guardiao_prs.absorvido_pela_main("pr") is False
