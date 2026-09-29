"""Lê o Blueprint do Render (render.yaml) sem depender de PyYAML.

Uso:
    python -m devagent.adaptadores.render_blueprint start   # startCommand
    python -m devagent.adaptadores.render_blueprint saude   # healthCheckPath

Lê só o primeiro serviço. Serve para o smoke test do CI subir a aplicação com
o mesmo comando que o Render usa.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

CAMPOS = {"start": "startCommand", "saude": "healthCheckPath"}
PADROES = {"saude": "/healthz"}


def ler(campo: str, arquivo: Path = Path("render.yaml")) -> str | None:
    if not arquivo.is_file():
        return None
    chave = CAMPOS[campo]
    for linha in arquivo.read_text(encoding="utf-8").splitlines():
        m = re.match(rf"\s*-?\s*{chave}\s*:\s*(.+?)\s*$", linha)
        if m:
            valor = m.group(1)
            if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in "\"'":
                valor = valor[1:-1]
            return valor
    return None


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 1 or args[0] not in CAMPOS:
        print(f"uso: render_blueprint {{{'|'.join(CAMPOS)}}}", file=sys.stderr)
        return 2
    valor = ler(args[0]) or PADROES.get(args[0])
    if not valor:
        print(f"{CAMPOS[args[0]]} não encontrado em render.yaml", file=sys.stderr)
        return 1
    print(valor)
    return 0


if __name__ == "__main__":
    sys.exit(main())
