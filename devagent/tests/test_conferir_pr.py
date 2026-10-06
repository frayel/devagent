"""Regras de disciplina do ciclo (devagent/conferir_pr.py) num repositório de brinquedo."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from devagent.conferir_pr import conferir, entradas_correcoes

BACKLOG_COM_CORRECAO = """# Backlog

## Correções (prioridade sobre qualquer feature)

- **Defeito conhecido.** Implementar a spec `docs/specs/002-b.md`.

## Features

- ideia qualquer
"""

BACKLOG_SEM_CORRECAO = """# Backlog

## Correções (prioridade sobre qualquer feature)

## Features

- ideia qualquer
"""


def spec(numero: int, status: str) -> str:
    return f"---\nid: {numero:03d}\ntitulo: Spec {numero}\nstatus: {status}\n---\n\nTexto.\n"


def git(raiz: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=raiz, check=True, capture_output=True)


def escrever(raiz: Path, arquivos: dict[str, str]) -> None:
    for caminho, texto in arquivos.items():
        alvo = raiz / caminho
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_text(texto, encoding="utf-8")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    git(tmp_path, "init", "-q", "-b", "main")
    git(tmp_path, "config", "user.email", "t@t")
    git(tmp_path, "config", "user.name", "t")
    escrever(
        tmp_path,
        {
            "docs/specs/001-a.md": spec(1, "ready"),
            "docs/specs/002-b.md": spec(2, "ready"),
            "docs/BACKLOG.md": BACKLOG_SEM_CORRECAO,
            "docs/STATE.md": "# Estado\n",
            "CHANGELOG.md": "# Changelog\n",
            "tests/test_ok.py": "def test_ok():\n    pass\n",
        },
    )
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "base")
    git(tmp_path, "branch", "base")
    git(tmp_path, "checkout", "-q", "-b", "trabalho")
    return tmp_path


def fechar(
    repo: Path, numero: int = 1, changelog: bool = True, estado: bool = True
) -> None:
    arquivos = {f"docs/specs/{numero:03d}-{'ab'[numero - 1]}.md": spec(numero, "done")}
    if changelog:
        arquivos["CHANGELOG.md"] = f"# Changelog\n- feat: entrega (Spec {numero:03d})\n"
    if estado:
        arquivos["docs/STATE.md"] = f"# Estado\n- Spec {numero:03d}\n"
    escrever(repo, arquivos)


def test_pr_completo_passa(repo: Path) -> None:
    fechar(repo)
    assert conferir(repo, "base").falhas == []


def test_spec_in_progress_reprova(repo: Path) -> None:
    escrever(repo, {"docs/specs/001-a.md": spec(1, "in-progress")})
    falhas = conferir(repo, "base").falhas
    assert any("001-a.md" in f and "in-progress" in f for f in falhas)


def test_script_de_teste_fora_de_tests_reprova(repo: Path) -> None:
    escrever(repo, {"test_explorar.py": "print(1)\n"})
    falhas = conferir(repo, "base").falhas
    assert any("test_explorar.py" in f for f in falhas)


def test_teste_dentro_de_subpasta_tests_passa(repo: Path) -> None:
    escrever(repo, {"pacote/tests/test_x.py": "def test_x():\n    pass\n"})
    assert conferir(repo, "base").falhas == []


def test_spec_done_sem_changelog_reprova(repo: Path) -> None:
    fechar(repo, changelog=False)
    falhas = conferir(repo, "base").falhas
    assert any("CHANGELOG" in f and "spec 1" in f for f in falhas)


def test_changelog_precisa_citar_o_numero_certo(repo: Path) -> None:
    fechar(repo)
    escrever(repo, {"CHANGELOG.md": "# Changelog\n- feat: entrega (Spec 010)\n"})
    falhas = conferir(repo, "base").falhas
    assert any("CHANGELOG" in f for f in falhas)


def test_spec_done_sem_estado_reprova(repo: Path) -> None:
    fechar(repo, estado=False)
    falhas = conferir(repo, "base").falhas
    assert any("STATE.md" in f for f in falhas)


def test_correcao_pendente_impede_spec_nova(repo: Path) -> None:
    git(repo, "checkout", "-q", "base")
    escrever(repo, {"docs/BACKLOG.md": BACKLOG_COM_CORRECAO})
    git(repo, "commit", "-qam", "correcao")
    git(repo, "branch", "-f", "trabalho")
    git(repo, "checkout", "-q", "trabalho")
    fechar(repo, 1)
    falhas = conferir(repo, "HEAD").falhas
    assert any("Correções" in f for f in falhas)


def test_resolver_a_correcao_libera(repo: Path) -> None:
    git(repo, "checkout", "-q", "base")
    escrever(repo, {"docs/BACKLOG.md": BACKLOG_COM_CORRECAO})
    git(repo, "commit", "-qam", "correcao")
    git(repo, "checkout", "-q", "-B", "trabalho")
    fechar(repo, 2)
    escrever(repo, {"docs/BACKLOG.md": BACKLOG_SEM_CORRECAO})
    assert conferir(repo, "HEAD").falhas == []


def test_fechar_spec_ja_em_andamento_e_continuidade(repo: Path) -> None:
    git(repo, "checkout", "-q", "base")
    escrever(
        repo,
        {
            "docs/BACKLOG.md": BACKLOG_COM_CORRECAO,
            "docs/specs/001-a.md": spec(1, "in-progress"),
        },
    )
    git(repo, "commit", "-qam", "base com spec aberta")
    git(repo, "checkout", "-q", "-B", "trabalho")
    fechar(repo, 1)
    assert conferir(repo, "HEAD").falhas == []


def test_entrada_bloqueada_nao_conta() -> None:
    texto = BACKLOG_COM_CORRECAO.replace(
        "002-b.md`.", "002-b.md`. Aguarda issue `bloqueado` #9."
    )
    assert entradas_correcoes(texto, "Correções") == []


def test_sem_base_so_regras_da_arvore(repo: Path) -> None:
    fechar(repo, changelog=False, estado=False)
    res = conferir(repo, "ref-que-nao-existe-e-sem-origin")
    assert res.falhas == []
    assert res.avisos
