"""Cada ADR do núcleo tem número próprio e aparece no índice do CICLO.md.

Dois PRs paralelos registraram ADRs diferentes com o mesmo número 031, e o
índice passou a citar "031" duas vezes: quem lia "ADR 031" num comentário não
sabia qual decisão era. Este teste reprova o número repetido e o ADR que não
está no índice da seção 9 do CICLO.md.
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

NUCLEO = Path(__file__).resolve().parent.parent
DECISOES = NUCLEO / "decisoes"


def _numeros() -> list[str]:
    numeros = []
    for adr in sorted(DECISOES.glob("*.md")):
        achado = re.match(r"(\d{3})-", adr.name)
        if achado:
            numeros.append(achado.group(1))
    return numeros


def test_numero_de_adr_nao_se_repete():
    repetidos = sorted(n for n, vezes in Counter(_numeros()).items() if vezes > 1)
    assert not repetidos, (
        f"ADRs com número repetido em devagent/decisoes/: {repetidos}. "
        "Renumere o mais novo para o próximo número livre e atualize as citações."
    )


def test_todo_adr_esta_no_indice_do_ciclo():
    ciclo = (NUCLEO / "CICLO.md").read_text(encoding="utf-8")
    linha = next(
        li for li in ciclo.splitlines() if li.startswith("| `devagent/decisoes/`")
    )
    faltando = [n for n in _numeros() if f"`{n}`" not in linha]
    assert not faltando, f"ADRs fora do índice da seção 9 do CICLO.md: {faltando}"
