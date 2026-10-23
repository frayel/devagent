from app.services.consultor_opinioes import (
    get_llm_uso_hoje,
    incrementar_llm_uso,
    set_opinioes_status,
    get_materias_nao_processadas,
    marcar_como_processada,
    save_opiniao,
)
from unittest.mock import patch, MagicMock


@patch("app.services.consultor_opinioes.get_connection")
def test_postgres_sql_syntax(mock_get_conn):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_get_conn.return_value = (mock_conn, "postgres")

    get_llm_uso_hoje()
    sql = mock_cursor.execute.call_args[0][0]
    assert "?" not in sql
    assert sql.count("%s") == len(mock_cursor.execute.call_args[0][1])

    incrementar_llm_uso()
    sql = mock_cursor.execute.call_args[0][0]
    assert "?" not in sql
    assert "INSERT OR" not in sql
    assert "ON CONFLICT" in sql
    assert sql.count("%s") == len(mock_cursor.execute.call_args[0][1])

    set_opinioes_status("ok")
    sql = mock_cursor.execute.call_args_list[-1][0][0]
    assert "?" not in sql
    assert sql.count("%s") == len(mock_cursor.execute.call_args_list[-1][0][1])

    get_materias_nao_processadas()
    sql = mock_cursor.execute.call_args[0][0]
    assert "?" not in sql

    marcar_como_processada("abc")
    sql = mock_cursor.execute.call_args[0][0]
    assert "?" not in sql
    assert sql.count("%s") == len(mock_cursor.execute.call_args[0][1])

    mock_cursor.fetchone.return_value = None
    save_opiniao(
        "guid", "PETR4", "BTG", "compra", 40.0, "resumo", "trecho", "2023-10-01", "http"
    )

    # check SELECT
    select_sql = mock_cursor.execute.call_args_list[-2][0][0]
    assert "?" not in select_sql

    # check INSERT
    insert_sql = mock_cursor.execute.call_args_list[-1][0][0]
    assert "?" not in insert_sql
    assert "INSERT OR" not in insert_sql
    assert "ON CONFLICT" in insert_sql
    assert insert_sql.count("%s") == len(mock_cursor.execute.call_args_list[-1][0][1])
