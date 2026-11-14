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
