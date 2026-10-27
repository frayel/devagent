1. **Mock collectors in tests:** Execute the following bash commands to mock `consultor_opinioes` and `radar_exaustao_alta` in `tests/test_agendador.py` and `tests/test_pagina_ponta_a_ponta.py` to stop them from making real network calls, and verify with `git diff`:
```bash
cat << 'HEREDOC' > patch_agendador.py
import re
with open("tests/test_agendador.py", "r") as f:
    content = f.read()
old_func = '    monkeypatch.setattr("app.collectors.correlacao_di.collect_and_save", lambda: True)\n    from app import agendador'
new_func = '    monkeypatch.setattr("app.collectors.correlacao_di.collect_and_save", lambda: True)\n    monkeypatch.setattr("app.collectors.consultor_opinioes.collect_and_save", lambda: True)\n    monkeypatch.setattr("app.collectors.radar_exaustao_alta.collect_and_save", lambda: True)\n    from app import agendador'
content = content.replace(old_func, new_func)

old_list = '            "concentracao_ordens",\n            "exaustao_tendencia",\n            "radar_anomalia_fechamento",\n            "correlacao_di",\n            "consultor_historico",\n            "exaustao_queda",\n            "fator_mola",\n        ):\n            monkeypatch.setattr(f"app.collectors.{nome}.collect_and_save", lambda: True)'
new_list = '            "concentracao_ordens",\n            "exaustao_tendencia",\n            "radar_anomalia_fechamento",\n            "correlacao_di",\n            "consultor_historico",\n            "exaustao_queda",\n            "fator_mola",\n            "radar_exaustao_alta",\n        ):\n            monkeypatch.setattr(f"app.collectors.{nome}.collect_and_save", lambda: True)'
content = content.replace(old_list, new_list)

old_falha = '    monkeypatch.setattr(\n        "app.collectors.armadilha_abertura.collect_and_save", lambda: True\n    )\n    monkeypatch.setattr(\n        "app.collectors.consultor_fechamento.collect_and_save", lambda: True\n    )'
new_falha = '    monkeypatch.setattr(\n        "app.collectors.armadilha_abertura.collect_and_save", lambda: True\n    )\n    monkeypatch.setattr("app.collectors.consultor_opinioes.collect_and_save", lambda: True)\n    monkeypatch.setattr("app.collectors.radar_exaustao_alta.collect_and_save", lambda: True)\n    monkeypatch.setattr(\n        "app.collectors.consultor_fechamento.collect_and_save", lambda: True\n    )\n    monkeypatch.setattr("app.collectors.radar_anomalias_spread.collect_and_save", lambda: True)\n    monkeypatch.setattr("app.collectors.exaustao_tendencia.collect_and_save", lambda: True)\n    monkeypatch.setattr("app.collectors.exaustao_queda.collect_and_save", lambda: True)'
content = content.replace(old_falha, new_falha)
with open("tests/test_agendador.py", "w") as f:
    f.write(content)

with open("tests/test_pagina_ponta_a_ponta.py", "r") as f:
    content = f.read()
old1 = '    yahoo_falso.instalar(monkeypatch)\n    monkeypatch.setattr(\n        "app.collectors.consultor_historico.collect_and_save", lambda: True\n    )\n    agendador.coletar_tudo()'
new1 = '    yahoo_falso.instalar(monkeypatch)\n    monkeypatch.setattr(\n        "app.collectors.consultor_historico.collect_and_save", lambda: True\n    )\n    monkeypatch.setattr(\n        "app.collectors.consultor_opinioes.collect_and_save", lambda: True\n    )\n    agendador.coletar_tudo()'
content = content.replace(old1, new1)
with open("tests/test_pagina_ponta_a_ponta.py", "w") as f:
    f.write(content)
HEREDOC
python patch_agendador.py
rm patch_agendador.py
git diff tests/test_agendador.py tests/test_pagina_ponta_a_ponta.py
```

2. **Network blocking via `socket`:**
   - Execute the following bash commands to add a new `autouse=True` fixture in `tests/conftest.py` that disables real socket connections, and verify with `git diff`:
```bash
cat << 'HEREDOC' > patch_conftest.py
with open("tests/conftest.py", "r") as f:
    content = f.read()
new_fixture = """
@pytest.fixture(autouse=True)
def _bloquear_rede(monkeypatch, request):
    if request.node.get_closest_marker("rede"):
        return

    import socket

    original_socket = socket.socket

    class BlockedSocket(original_socket):
        def connect(self, address):
            host = address[0] if isinstance(address, tuple) else address
            if host not in ("127.0.0.1", "localhost", "::1"):
                raise RuntimeError(f"teste tentou chamar a rede: {host}")
            super().connect(address)

    monkeypatch.setattr(socket, "socket", BlockedSocket)
"""
content += new_fixture
with open("tests/conftest.py", "w") as f:
    f.write(content)
HEREDOC
python patch_conftest.py
rm patch_conftest.py
git diff tests/conftest.py
```

3. **Exclude network tests from `make verify`:** In the `Makefile`, modify `pytest -q` to `pytest -m "not rede" -q` under `verify` using `sed -i 's/pytest -q/pytest -m "not rede" -q/g' Makefile`, and verify with `git diff Makefile`.

4. **Add pytest mark registration:** In `pytest.ini`, register the `rede` marker using `echo -e "\nmarkers =\n    rede: mark a test as requiring network access." >> pytest.ini`, and verify with `cat pytest.ini`.

5. **Test for network block and new acceptance test:**
   - Create `tests/test_aceite_095.py` via a bash heredoc command with the exact test content to ensure that a plain `httpx.get("https://example.com")` fails with the expected blocking message and ensure that tests with the `rede` mark can bypass the block. Verify with `cat tests/test_aceite_095.py`.
```bash
cat << 'HEREDOC' > tests/test_aceite_095.py
import pytest
import httpx

def test_bloqueio_rede():
    with pytest.raises(RuntimeError) as exc:
        httpx.get("https://example.com")
    assert "teste tentou chamar a rede" in str(exc.value)

@pytest.mark.rede
def test_rede_liberada():
    # This test should pass when running tests with the 'rede' mark
    pass
HEREDOC
cat tests/test_aceite_095.py
```

6. **Update documentation:** Modify `PRODUTO.md` in the "Testes" section to explicitly state that tests cannot use the network and must be marked with `@pytest.mark.rede` using `sed -i 's/testes não acessam a internet/testes não acessam a internet (exceto os marcados com @pytest.mark.rede)/g' PRODUTO.md`, and verify with `git diff PRODUTO.md`.

7. **Execute `make verify` and `make smoke` in the bash session** to ensure that `make verify` correctly blocks the network and everything still passes without internet.

8. **Complete pre-commit steps to ensure proper testing, verification, review, and reflection are done.**

9. **Submit PR:** Submit the changes using the `submit` tool with the title `⚡ Bolt: Testes sem internet (spec 095)` and description reflecting the fixes.
