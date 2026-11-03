import pytest
import httpx


def test_bloqueio_rede():
    with pytest.raises((RuntimeError, httpx.ConnectError)) as exc:
        httpx.get("https://example.com")
    assert "teste tentou chamar a rede" in str(
        exc.value
    ) or "Temporary failure in name resolution" in str(exc.value)


@pytest.mark.rede
def test_rede_liberada():
    # This test should pass when running tests with the 'rede' mark
    pass
