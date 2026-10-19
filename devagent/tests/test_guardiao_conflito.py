"""Conflito só de acréscimo não conta como conflito grande.

Reproduz o caso de 19/10: o #362 (spec 068b) e o #358 (página de sistema)
acrescentaram, cada um, um bloco no fim de `tema.css` no mesmo ponto. O
guardião mediu 93 linhas e fechou o PR, embora bastasse manter os dois blocos.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

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


BASE_CSS = "".join(f".regra-{i} {{ cor: {i}; }}\n" for i in range(10))
BASE_STATE = "## Experiência\n\n- Acrescentados desde a última revisão: 0.\n"


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    git(tmp_path, "init", "-q", "-b", "main")
    git(tmp_path, "config", "user.email", "t@t")
    git(tmp_path, "config", "user.name", "t")
    escrever(tmp_path, "tema.css", BASE_CSS)
    escrever(tmp_path, "STATE.md", BASE_STATE)
    commit(tmp_path, "base")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def bloco(nome: str, n: int) -> str:
    return "".join(f".{nome}-{i} {{ margem: {i}; }}\n" for i in range(n))


def cenario_362(repo: Path, mexer_no_contador: bool) -> None:
    git(repo, "checkout", "-q", "-b", "pr")
    escrever(repo, "tema.css", BASE_CSS + bloco("consultor", 50))
    if mexer_no_contador:
        escrever(repo, "STATE.md", BASE_STATE.replace("0.", "1."))
    commit(repo, "consultor")
    git(repo, "checkout", "-q", "main")
    escrever(repo, "tema.css", BASE_CSS + bloco("sistema", 40))
    if mexer_no_contador:
        escrever(repo, "STATE.md", BASE_STATE.replace("0.", "1 (Sistema)."))
    commit(repo, "sistema")


def test_acrescimo_dos_dois_lados_nao_mede_tamanho(repo: Path):
    cenario_362(repo, mexer_no_contador=False)
    arquivos, reais, acrescimo = guardiao_prs.medir_conflito_entre("main", "pr")
    assert arquivos == ["tema.css"]
    assert reais == 0
    assert acrescimo == 90
    assert reais <= guardiao_prs.CONFLITO_MAX_LINHAS


def test_linha_alterada_dos_dois_lados_continua_contando(repo: Path):
    cenario_362(repo, mexer_no_contador=True)
    arquivos, reais, acrescimo = guardiao_prs.medir_conflito_entre("main", "pr")
    assert sorted(arquivos) == ["STATE.md", "tema.css"]
    assert reais == 2
    assert acrescimo == 90


def test_edicao_concorrente_grande_continua_grande(repo: Path):
    git(repo, "checkout", "-q", "-b", "pr")
    escrever(repo, "tema.css", BASE_CSS.replace("cor:", "cor-pr:"))
    commit(repo, "pr reescreve")
    git(repo, "checkout", "-q", "main")
    escrever(repo, "tema.css", BASE_CSS.replace("cor:", "cor-main:"))
    commit(repo, "main reescreve")
    _, reais, acrescimo = guardiao_prs.medir_conflito_entre("main", "pr")
    assert reais == 20
    assert acrescimo == 0


def test_merge_limpo_devolve_none(repo: Path):
    git(repo, "checkout", "-q", "-b", "pr")
    escrever(repo, "outro.css", "x\n")
    commit(repo, "outro")
    assert guardiao_prs.medir_conflito_entre("main", "pr") is None


def test_contar_conflito_separa_os_trechos():
    texto = (
        "a\n<<<<<<< HEAD\nnovo1\nnovo2\n||||||| base\n=======\nnovo3\n>>>>>>> pr\n"
        "b\n<<<<<<< HEAD\nx-main\n||||||| base\nx\n=======\nx-pr\n>>>>>>> pr\n"
    )
    assert guardiao_prs.contar_conflito(texto) == (2, 3)
