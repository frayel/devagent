import pytest


@pytest.fixture(autouse=True)
def setup_db(monkeypatch, tmp_path):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_PATH", str(db_path))

    # Reload database module to apply monkeypatch for DB_PATH at initialization time.
    # We must explicitly override DB_PATH in the app.database module because it is evaluated on import.
    import app.database

    monkeypatch.setattr(app.database, "DB_PATH", str(db_path))

    # Initialize the test database
    app.database.init_db()

    yield
