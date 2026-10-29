"""A página /sistema mostra a versão e o tamanho do banco em uso."""

from unittest.mock import MagicMock, patch

from app import banco
from app.services.sistema import verificar_banco


def test_versao_postgres_em_formato_legivel():
    assert banco.versao_postgres(160004) == "16.4"
    assert banco.versao_postgres(170000) == "17.0"
    assert banco.versao_postgres(90624) == "9.6.24"
    assert banco.versao_postgres(None) is None
    assert banco.versao_postgres(MagicMock()) is None


def test_diagnostico_postgres_traz_a_versao_da_conexao():
    banco._diagnostico_cache = None
    with (
        patch("app.banco.get_backend_type", return_value="postgres"),
        patch("app.banco.get_connection") as get_conn,
    ):
        conn = MagicMock()
        conn.info.server_version = 160004
        cursor = MagicMock()
        cursor.fetchone.side_effect = [[12], [5 * 1_048_576]]
        conn.cursor.return_value.__enter__.return_value = cursor
        get_conn.return_value = (conn, "postgres")

        info = banco.diagnostico()

    banco._diagnostico_cache = None
    assert info["versao"] == "16.4"
    assert info["tamanho"] == "5,0 MB"


def test_diagnostico_sqlite_traz_a_versao():
    import sqlite3

    banco._diagnostico_cache = None
    with patch("app.banco.get_backend_type", return_value="sqlite_efemero"):
        info = banco.diagnostico()
    banco._diagnostico_cache = None
    assert info["versao"] == sqlite3.sqlite_version


def test_item_do_banco_mostra_versao_e_tamanho():
    info = {
        "tipo": "Postgres",
        "versao": "16.4",
        "tamanho": "48,2 MB",
        "latencia_ms": 31,
        "tabelas": 14,
    }
    item = verificar_banco(info)
    assert item.resumo == "Postgres 16.4 · 48,2 MB · 31 ms"
    assert "48,2 MB" in item.detalhe


def test_item_do_banco_sem_versao_continua_legivel():
    item = verificar_banco({"tipo": "Postgres", "tamanho": "1 MB", "latencia_ms": 3})
    assert item.resumo == "Postgres · 1 MB · 3 ms"
