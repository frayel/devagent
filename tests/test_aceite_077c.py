from unittest.mock import patch, MagicMock
from app.banco import diagnostico
from app.services.sistema import verificar_banco


def test_diagnostico_postgres_sem_expor_url():
    with (
        patch("app.banco.get_backend_type", return_value="postgres"),
        patch("app.banco.get_connection") as mock_get_conn,
        patch("os.environ.get", return_value="postgres://test:test@localhost/test"),
    ):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = (mock_conn, "postgres")
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        mock_cursor.fetchone.side_effect = [[5], [2097152]]

        info = diagnostico()

        assert info["tipo"] == "Postgres"
        assert info["database_url"] is True
        assert "postgres://test" not in str(info)
        assert info["tabelas"] == 5
        assert info["tamanho"] == "2,0 MB"


def test_verificar_banco_ok_postgres():
    info = {"tipo": "Postgres", "tabelas": 2}
    item = verificar_banco(info)
    assert item.nivel == "ok"


def test_verificar_banco_atencao_sqlite_fallback():
    info = {"tipo": "SQLite", "database_url": True}
    item = verificar_banco(info)
    assert item.nivel == "atencao"
    assert "DATABASE_URL está configurado, mas o Postgres não respondeu" in item.detalhe
    assert "073 a 076" not in item.detalhe
