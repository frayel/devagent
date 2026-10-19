"""Fila de specs prontas: qual é a próxima a implementar (CICLO.md, Passo 4).

A ordem não fica a cargo da leitura do agente. O vigia põe a próxima spec no
prompt da sessão e o `estado_github` a repete no primeiro comando, para que
nenhuma sessão escreva spec nova (Passo 7) enquanto a fila não estiver vazia
(ADR 015).

Uso:
    python -m devagent.fila_specs     # lista as specs `ready` em ordem
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from devagent.conferir_pr import documentos, status_de

NUMERO = re.compile(r"0*(\d+)([a-z]*)")


def chave(caminho: Path) -> tuple[int, str, str]:
    """Ordem natural: 068a < 068b < 069 < 080 < 100."""
    m = NUMERO.match(caminho.name)
    if not m:
        return (sys.maxsize, "", caminho.name)
    return (int(m.group(1)), m.group(2), caminho.name)


def specs_prontas(raiz: Path | None = None) -> list[Path]:
    """Specs com `status: ready`, da próxima a implementar para a última."""
    raiz = raiz or Path.cwd()
    pasta = raiz / documentos()["specs"]
    if not pasta.is_dir():
        return []
    prontas = [
        p
        for p in pasta.glob("*.md")
        if status_de(p.read_text(encoding="utf-8")) == "ready"
    ]
    return sorted(prontas, key=chave)


def instrucao(prontas: list[Path], raiz: Path | None = None) -> str:
    """Frase que manda a sessão para o Passo 4; vazia se a fila está vazia."""
    if not prontas:
        return ""
    raiz = raiz or Path.cwd()
    try:
        proxima = prontas[0].relative_to(raiz)
    except ValueError:
        proxima = prontas[0]
    return (
        f"A fila tem {len(prontas)} spec(s) com status ready; a próxima é "
        f"{proxima.as_posix()}. Depois do Passo 1 (produção quebrada, correções, "
        "issue prioridade) e do Passo 2 (PR aberto do agente), o trabalho desta "
        "sessão é implementar essa spec pelo Passo 4. Enquanto houver spec ready, "
        "não escreva spec nova nem rode o Passo 7. Se a spec for grande demais, "
        "divida-a como manda o Passo 4."
    )


def main() -> int:
    prontas = specs_prontas()
    if not prontas:
        print("Nenhuma spec ready.")
        return 0
    for p in prontas:
        print(p.as_posix())
    return 0


if __name__ == "__main__":
    sys.exit(main())
