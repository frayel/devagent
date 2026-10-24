import pytest


@pytest.fixture(autouse=True)
def clean_env(monkeypatch, request):
    if "test_registro_que_fecha_issue" not in request.node.name:
        monkeypatch.delenv("GITHUB_EVENT_PATH", raising=False)
