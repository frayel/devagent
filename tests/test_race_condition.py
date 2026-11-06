import pytest
from unittest.mock import patch


@pytest.mark.asyncio
async def test_regression_coletar_synchronous_startup():
    import app.main as main_module

    with (
        patch("app.banco.abrir_pool"),
        patch("app.agendador.coleta_ligada", return_value=True),
        patch("app.agendador.coletar_tudo") as mock_coletar_tudo,
        patch("app.agendador.laco_de_coleta") as mock_laco,
        patch("app.collectors.sistema.laco_do_monitor"),
        patch("app.services.validador_gemini.laco_da_validacao"),
        patch("app.banco.fechar_pool"),
    ):
        lifespan_cm = main_module.lifespan(main_module.app)
        await lifespan_cm.__aenter__()

        mock_coletar_tudo.assert_called_once()
        mock_laco.assert_called_once_with(pular_primeira=True)

        await lifespan_cm.__aexit__(None, None, None)
