"""Nenhum teste grava o banco na raiz do repositório.

Este código de módulo roda na coleta, antes de qualquer fixture: é o mesmo
momento em que `import app.main` lê o banco pela primeira vez.
"""

import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CAMINHO_NA_COLETA = os.environ.get("DATABASE_PATH")


def test_banco_definido_antes_da_coleta_fora_do_repositorio():
    assert CAMINHO_NA_COLETA, "DATABASE_PATH precisa existir antes da coleta"
    caminho = Path(CAMINHO_NA_COLETA).resolve()
    assert RAIZ not in caminho.parents
