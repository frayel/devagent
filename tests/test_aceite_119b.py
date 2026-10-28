import asyncio
import os
from unittest import mock

import httpx
import pytest

from app.services import validador_gemini
from app.collectors import registro_fontes


@pytest.fixture(autouse=True)
def _limpar_registro():
    registro_fontes.limpar()


def test_sucesso_na_validacao():
    with mock.patch(
        "app.services.validador_gemini.gemini_modelo._listar_modelos"
    ) as mock_listar:

        def fake_listar(api_key):
            registro_fontes.sucesso("Gemini")
            return []

        mock_listar.side_effect = fake_listar

        with mock.patch.dict(os.environ, {"GEMINI_API_KEY": "fake-key"}):
            with mock.patch("app.database.save_gemini_validation") as mock_db:
                asyncio.run(validador_gemini.validar())

    f = registro_fontes.fontes().get("Gemini")
    assert f is not None
    assert f.recentes[-1] is True
    assert f.sucessos == 1
    mock_db.assert_called_once_with(sucesso=True, status=200)


def test_falha_na_validacao():
    with mock.patch(
        "app.services.validador_gemini.gemini_modelo._listar_modelos"
    ) as mock_listar:

        def fake_listar(api_key):
            registro_fontes.falha("Gemini", "HTTP 403", grave=True)
            raise httpx.HTTPStatusError(
                "403 Forbidden",
                request=mock.Mock(),
                response=mock.Mock(status_code=403),
            )

        mock_listar.side_effect = fake_listar

        with mock.patch.dict(os.environ, {"GEMINI_API_KEY": "fake-key"}):
            with mock.patch("app.database.save_gemini_validation") as mock_db:
                asyncio.run(validador_gemini.validar())

    f = registro_fontes.fontes().get("Gemini")
    assert f is not None
    assert f.recentes[-1] is False
    assert f.falhas == 1
    mock_db.assert_called_once_with(sucesso=False, status=403)


def test_ignorado_sem_chave():
    with mock.patch(
        "app.services.validador_gemini.gemini_modelo._listar_modelos"
    ) as mock_listar:
        with mock.patch.dict(os.environ, {}, clear=True):
            with mock.patch("app.database.save_gemini_validation") as mock_db:
                asyncio.run(validador_gemini.validar())

    assert not mock_listar.called
    assert "Gemini" not in registro_fontes.fontes()
    mock_db.assert_not_called()
