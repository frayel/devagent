"""`make install` não para quando o pip do sistema não se deixa atualizar.

No ambiente das sessões, `python -m pip install --upgrade pip` falha com
"Cannot uninstall pip 24.0, RECORD file not found" (pip do Debian). Como o
primeiro comando da execução é `make install`, essa falha impedia a instalação
das ferramentas fixadas e o `make verify` seguinte quebrava.
"""

import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent

PYTHON_FALSO = """#!/bin/sh
echo "$@" >> "$LOG_CHAMADAS"
case "$*" in
  *"--upgrade pip"*) echo "ERROR: Cannot uninstall pip 24.0, RECORD file not found." >&2; exit 1 ;;
esac
exit 0
"""


@pytest.mark.skipif(shutil.which("make") is None, reason="make ausente")
@pytest.mark.parametrize(
    "alvo,requisitos",
    [("install", "requirements-dev.txt"), ("install-prod", "requirements.txt")],
)
def test_install_segue_quando_o_pip_nao_atualiza(tmp_path, alvo, requisitos):
    py = tmp_path / "python"
    py.write_text(PYTHON_FALSO)
    py.chmod(py.stat().st_mode | stat.S_IEXEC)
    log = tmp_path / "chamadas.log"

    res = subprocess.run(
        ["make", "-s", alvo, f"PY={py}"],
        cwd=RAIZ,
        env={**os.environ, "LOG_CHAMADAS": str(log)},
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert res.returncode == 0, res.stderr
    chamadas = log.read_text().splitlines()
    assert any("--upgrade pip" in c for c in chamadas)
    assert chamadas[-1] == f"-m pip install -r {requisitos}"
