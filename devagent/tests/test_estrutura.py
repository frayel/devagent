"""Todo módulo do núcleo aparece na estrutura da seção 3 do CICLO.md.

A seção 3 é o mapa que o agente lê para saber onde as coisas moram. Ela
listava só quatro dos onze arquivos executáveis de `devagent/`: `saude.py`,
`conferir_pr.py`, `fila_specs.py`, `cadencias.py`, `raias.py`, `aceite.py` e
`instalar.py` nasceram em PRs que atualizaram o índice de ADRs mas não o
mapa. Este teste reprova o módulo novo que não entra no mapa.
"""

from __future__ import annotations

import re
from pathlib import Path

NUCLEO = Path(__file__).resolve().parent.parent


def _bloco_da_estrutura() -> str:
    ciclo = (NUCLEO / "CICLO.md").read_text(encoding="utf-8")
    secao = ciclo.split("## 3. Estrutura comum", 1)[1].split("\n## ", 1)[0]
    achado = re.search(r"```\n(.*?)```", secao, re.DOTALL)
    assert achado, "a seção 3 do CICLO.md perdeu o bloco com a estrutura"
    return achado.group(1)


def test_todo_modulo_do_nucleo_esta_na_estrutura():
    bloco = _bloco_da_estrutura()
    arquivos = sorted(
        p.name
        for p in NUCLEO.iterdir()
        if p.is_file() and p.suffix in {".py", ".sh"} and p.name != "__init__.py"
    )
    faltando = [
        nome
        for nome in arquivos
        if not re.search(rf"^\s+{re.escape(nome)}\s", bloco, re.M)
    ]
    assert not faltando, (
        f"Arquivos de devagent/ fora da estrutura da seção 3 do CICLO.md: {faltando}. "
        "Acrescente uma linha com o nome e para que serve."
    )


def test_toda_pasta_do_nucleo_esta_na_estrutura():
    bloco = _bloco_da_estrutura()
    pastas = sorted(
        p.name
        for p in NUCLEO.iterdir()
        if p.is_dir() and not p.name.startswith((".", "_"))
    )
    faltando = [
        nome
        for nome in pastas
        if not re.search(rf"^\s+{re.escape(nome)}/\s", bloco, re.M)
    ]
    assert not faltando, (
        f"Pastas de devagent/ fora da estrutura da seção 3 do CICLO.md: {faltando}"
    )


# Os índices de skills e contextos são o outro mapa que o agente lê para se
# orientar: a seção 9 do CICLO.md lista `devagent/skills/` e o PRODUTO.md lista
# `docs/context/` e `docs/skills/`. Ambos pedem "acrescente-o a esta tabela no
# mesmo PR", e nenhum teste conferia; a retrospectiva de
# docs/runs/2026-11-14-0839.md propôs estender a checagem a eles.

RAIZ = NUCLEO.parent


def _faltando_no_indice(pasta: Path, texto: str) -> list[str]:
    if not pasta.is_dir():
        return []
    prefixo = pasta.relative_to(RAIZ).as_posix()
    return sorted(
        p.name for p in pasta.glob("*.md") if f"`{prefixo}/{p.name}`" not in texto
    )


def test_toda_skill_do_nucleo_esta_no_indice_da_secao_9():
    ciclo = (NUCLEO / "CICLO.md").read_text(encoding="utf-8")
    assert "## 9." in ciclo, "o CICLO.md perdeu a seção 9 (índice do núcleo)"
    secao = ciclo.split("## 9.", 1)[1]
    faltando = _faltando_no_indice(NUCLEO / "skills", secao)
    assert not faltando, (
        f"Skills de devagent/skills/ fora do índice da seção 9 do CICLO.md: {faltando}. "
        "Acrescente uma linha com o arquivo, para que serve e quando ler."
    )


def test_todo_contexto_e_skill_do_projeto_esta_no_indice_do_produto():
    produto = RAIZ / "PRODUTO.md"
    if not produto.is_file():
        return
    texto = produto.read_text(encoding="utf-8")
    faltando = _faltando_no_indice(RAIZ / "docs" / "context", texto)
    faltando += _faltando_no_indice(RAIZ / "docs" / "skills", texto)
    assert not faltando, (
        f"Arquivos de docs/context/ ou docs/skills/ fora do índice do PRODUTO.md: {faltando}. "
        "Acrescente-os à tabela de índice no mesmo PR."
    )
