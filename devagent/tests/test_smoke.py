"""O smoke encerra o servidor que subiu e não confere um servidor alheio."""

import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

SMOKE = Path(__file__).resolve().parents[1] / "smoke.sh"

SERVIDOR = """
import http.server, os
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers(); self.wfile.write(b"ok")
    def log_message(self, *a):
        pass
http.server.HTTPServer(("127.0.0.1", int(os.environ["PORT"])), H).serve_forever()
"""

pytestmark = pytest.mark.skipif(
    not (shutil.which("curl") and shutil.which("pgrep")),
    reason="precisa de curl e pgrep",
)


def _porta_livre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _responde(porta: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{porta}/healthz", timeout=1):
            return True
    except OSError:
        return False


def _smoke(tmp_path: Path, porta: int) -> subprocess.CompletedProcess:
    (tmp_path / "servidor.py").write_text(SERVIDOR, encoding="utf-8")
    # Comando composto: o `sh -c` não faz exec, e o servidor vira processo filho.
    inicio = f"cd {tmp_path} && {sys.executable} servidor.py"
    return subprocess.run(
        ["sh", str(SMOKE)],
        cwd=tmp_path,
        env={"PATH": "/usr/bin:/bin", "PORT": str(porta), "SMOKE_START": inicio},
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_smoke_encerra_o_servidor_filho(tmp_path):
    porta = _porta_livre()
    resultado = _smoke(tmp_path, porta)
    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
    for _ in range(20):
        if not _responde(porta):
            break
        time.sleep(0.1)
    assert not _responde(porta), "o servidor do smoke continuou de pé segurando a porta"


def test_smoke_reprova_porta_ja_ocupada(tmp_path):
    porta = _porta_livre()
    (tmp_path / "servidor.py").write_text(SERVIDOR, encoding="utf-8")
    alheio = subprocess.Popen(
        [sys.executable, str(tmp_path / "servidor.py")], env={"PORT": str(porta)}
    )
    try:
        for _ in range(50):
            if _responde(porta):
                break
            time.sleep(0.1)
        resultado = _smoke(tmp_path, porta)
        assert resultado.returncode == 1
        assert "ocupada" in resultado.stdout
    finally:
        alheio.kill()
        alheio.wait()
