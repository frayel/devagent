import pytest
from jinja2 import StrictUndefined


@pytest.fixture(autouse=True)
def setup_db(monkeypatch, tmp_path):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_PATH", str(db_path))

    # Reload database module to apply monkeypatch for DB_PATH at initialization time.
    # We must explicitly override DB_PATH in the app.database module because it is evaluated on import.
    import app.database

    monkeypatch.setattr(app.database, "DB_PATH", str(db_path))

    # Initialize the test database
    import app.banco

    app.banco._db_initialized = False
    app.database.init_db()

    # O MT5 só entra nos testes que o configuram de propósito.
    for var in ("MT5_API_URL", "MT5_API_KEY", "MT5_SIMBOLOS", "MT5_FUSO_SERVIDOR"):
        monkeypatch.delenv(var, raising=False)
    from app.collectors import mt5

    mt5.limpar_cache()
    mt5.reiniciar_rastreio()

    # A descoberta do modelo Gemini nunca vai à rede nos testes.
    monkeypatch.delenv("GEMINI_MODELO", raising=False)
    from app.services import gemini_modelo

    gemini_modelo.limpar()
    monkeypatch.setattr(
        gemini_modelo,
        "_listar_modelos",
        lambda api_key: [
            {
                "name": "models/gemini-3.5-flash-lite",
                "supportedGenerationMethods": ["generateContent"],
            }
        ],
    )

    yield


class _IndefinidoDeTeste(StrictUndefined):
    """Atributo inexistente só pode ser testado, nunca usado.

    `{% if x.opcional %}`, `x is defined` e `x | default(...)` continuam
    funcionando, porque as macros dependem de chaves opcionais. Imprimir,
    comparar, formatar ou fazer conta com um atributo que não existe falha
    no teste, em vez de virar texto vazio ou um 500 em produção.
    """

    def __bool__(self) -> bool:
        return False


@pytest.fixture(autouse=True)
def _templates_estritos(monkeypatch):
    from app.main import templates

    monkeypatch.setattr(templates.env, "undefined", _IndefinidoDeTeste)


@pytest.fixture(autouse=True)
def _bloquear_rede(monkeypatch, request):
    if request.node.get_closest_marker("rede"):
        return

    import socket

    original_socket = socket.socket

    class BlockedSocket(original_socket):
        def connect(self, address):
            host = address[0] if isinstance(address, tuple) else address
            if host not in ("127.0.0.1", "localhost", "::1", "testserver"):
                raise RuntimeError(f"teste tentou chamar a rede: {host}")
            super().connect(address)

    monkeypatch.setattr(socket, "socket", BlockedSocket)
