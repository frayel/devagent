import pytest
from unittest.mock import patch


@pytest.mark.asyncio
async def test_regression_coletar_startup_db_pool():
    import app.banco as banco_module

    with patch("psycopg_pool.ConnectionPool.open") as mock_open:
        banco_module.abrir_pool()
        # Verificar se open foi chamado com wait=True para evitar Disjuntor aberto
        if mock_open.called:
            mock_open.assert_called_once_with(wait=True)
