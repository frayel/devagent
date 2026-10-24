import pytest
import os


@pytest.fixture(autouse=True)
def clean_github_env():
    """Limpa variáveis de ambiente do GitHub Actions para que os testes não leiam o PR de verdade."""
    original_event_path = os.environ.get("GITHUB_EVENT_PATH")
    original_event_name = os.environ.get("GITHUB_EVENT_NAME")

    if "GITHUB_EVENT_PATH" in os.environ:
        del os.environ["GITHUB_EVENT_PATH"]
    if "GITHUB_EVENT_NAME" in os.environ:
        del os.environ["GITHUB_EVENT_NAME"]

    yield

    if original_event_path is not None:
        os.environ["GITHUB_EVENT_PATH"] = original_event_path
    if original_event_name is not None:
        os.environ["GITHUB_EVENT_NAME"] = original_event_name
