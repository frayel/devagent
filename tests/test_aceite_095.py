import pytest
import httpx


def test_bloqueio_rede():
    with pytest.raises(RuntimeError) as exc:
        httpx.get("https://example.com")
    assert "teste tentou chamar a rede" in str(exc.value)


@pytest.mark.rede
def test_rede_liberada():
    """Com a marca `rede`, o `_bloquear_rede` do conftest não troca o socket."""
    import socket

    assert socket.socket.__name__ != "BlockedSocket"
    assert socket.getaddrinfo.__name__ != "mock_getaddrinfo"
