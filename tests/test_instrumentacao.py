import pytest
from datetime import datetime, timezone

from app.database import init_db, save_coleta_vazia, get_coletas_vazias_count


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", str(tmp_path / "test.db"))
    init_db()
    yield


def test_save_coleta_vazia(temp_db):
    save_coleta_vazia("test_panel", datetime.now(timezone.utc))
    save_coleta_vazia("test_panel", datetime.now(timezone.utc))
    assert get_coletas_vazias_count("test_panel") == 2
    assert get_coletas_vazias_count("other_panel") == 0
