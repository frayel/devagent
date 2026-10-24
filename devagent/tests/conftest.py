import pytest


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    monkeypatch.delenv("GITHUB_EVENT_PATH", raising=False)
