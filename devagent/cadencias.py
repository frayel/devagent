"""Contadores das cadências do Passo 7, calculados a partir das specs (ADR 024).

Os contadores viviam no `docs/STATE.md`, editados à mão por duas raias: o
desenvolvimento somava ao entregar e o Especificador zerava ao escrever a spec
de cadência. Era uma mesma linha alterada pelos dois lados, conflito real.
Agora ninguém os escreve; eles saem do `status:` e da `gaveta:` das specs:

    experiência  specs `done` da gaveta *capacidade nova* desde a última spec
                 `done` da gaveta *experiência* (cadência vence com 3)
    manutenção   specs `done` que não são de manutenção desde a última spec
                 `done` das gavetas *saúde técnica* ou *poda* (vence com 4)

A ordem é a dos números das specs (068a < 068b < 069), a mesma da fila.

Uso:
    python -m devagent.cadencias

Só usa a biblioteca padrão.
"""

from __future__ import annotations

import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from devagent.conferir_pr import documentos
from devagent.fila_specs import chave

EXPERIENCIA_VENCE = 3
MANUTENCAO_VENCE = 4

GAVETA = re.compile(r"^gaveta:\s*(.*?)\s*$", re.MULTILINE)
STATUS = re.compile(r"^status:\s*([\w-]+)\s*$", re.MULTILINE)


def _normal(texto: str) -> str:
    sem = "".join(
        c for c in unicodedata.normalize("NFD", texto) if not unicodedata.combining(c)
    )
    return sem.strip().lower()


MANUTENCAO = {"saude tecnica", "poda"}


@dataclass(frozen=True)
class Cadencias:
    experiencia: int
    manutencao: int

    @property
    def vencidas(self) -> list[str]:
        """Cadências vencidas, a de manutenção primeiro (CICLO.md, Passo 7)."""
        v = []
        if self.manutencao >= MANUTENCAO_VENCE:
            v.append("manutenção")
        if self.experiencia >= EXPERIENCIA_VENCE:
            v.append("experiência")
        return v


def entregues(raiz: Path | None = None) -> list[tuple[Path, str]]:
    """(spec, gaveta normalizada) das specs `done`, na ordem da fila."""
    pasta = (raiz or Path.cwd()) / documentos()["specs"]
    if not pasta.is_dir():
        return []
    feitas = []
    for p in pasta.glob("*.md"):
        texto = p.read_text(encoding="utf-8")
        st = STATUS.search(texto)
        if not st or st.group(1) != "done":
            continue
        g = GAVETA.search(texto)
        feitas.append((p, _normal(g.group(1)) if g else ""))
    return sorted(feitas, key=lambda item: chave(item[0]))


def calcular(raiz: Path | None = None) -> Cadencias:
    feitas = entregues(raiz)
    experiencia = manutencao = 0
    for _, gaveta in feitas:
        if gaveta == "experiencia":
            experiencia = 0
        elif gaveta == "capacidade nova":
            experiencia += 1
        if gaveta in MANUTENCAO:
            manutencao = 0
        else:
            manutencao += 1
    return Cadencias(experiencia, manutencao)


def resumo(c: Cadencias) -> str:
    linhas = [
        f"Cadência de experiência: {c.experiencia} de {EXPERIENCIA_VENCE} "
        "specs de capacidade nova desde a última de experiência.",
        f"Cadência de manutenção: {c.manutencao} de {MANUTENCAO_VENCE} "
        "specs entregues desde a última de saúde técnica ou poda.",
    ]
    if c.vencidas:
        linhas.append(
            "Vencida(s): " + ", ".join(c.vencidas) + " (a primeira vai antes)."
        )
    return "\n".join(linhas)


def main() -> int:
    print(resumo(calcular()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
