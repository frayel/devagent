"""`make smoke` não cria `data.db` na raiz do repositório.

O alvo subia a aplicação sem `DATABASE_PATH`, e `app/database.py` cai no
caminho padrão `data.db` (relativo ao diretório atual, a raiz). Quatro
retrospectivas seguidas culparam a suíte de testes, porque a rodada roda o
`make smoke` logo depois do `make verify`.
"""

import os
import shutil
import socket
import stat
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent

# Faz o papel do `$(PY)` do Makefile: responde ao adaptador do blueprint com um
# servidor estático que registra o DATABASE_PATH que recebeu do alvo.
PYTHON_FALSO = """#!/bin/sh
case "$*" in
  *" start") echo 'echo "${DATABASE_PATH:-}" > "$REGISTRO" && exec "$PY_REAL" -m http.server "$PORT" --bind 127.0.0.1 --directory "$SITE"' ;;
  *" saude") echo "/healthz" ;;
  *) exit 1 ;;
esac
"""


def _porta_livre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@pytest.mark.skipif(
    shutil.which("make") is None or shutil.which("curl") is None,
    reason="make ou curl ausente",
)
def test_smoke_usa_banco_temporario(tmp_path):
    py = tmp_path / "python"
    py.write_text(PYTHON_FALSO)
    py.chmod(py.stat().st_mode | stat.S_IEXEC)
    site = tmp_path / "site"
    site.mkdir()
    (site / "healthz").write_text("ok")
    (site / "index.html").write_text("ok")
    registro = tmp_path / "database_path.txt"

    env = {k: v for k, v in os.environ.items() if k != "DATABASE_PATH"}
    env.update(
        REGISTRO=str(registro),
        PY_REAL=sys.executable,
        SITE=str(site),
        PORT=str(_porta_livre()),
    )
    res = subprocess.run(
        ["make", "-s", "smoke", f"PY={py}"],
        cwd=RAIZ,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert res.returncode == 0, res.stdout + res.stderr
    caminho = Path(registro.read_text().strip())
    assert caminho.name, "o alvo smoke precisa definir DATABASE_PATH"
    assert caminho.is_absolute()
    assert RAIZ not in caminho.parents, (
        f"banco do smoke dentro do repositório: {caminho}"
    )
