"""A página de saúde não mostra issue nem PR de estranho (repositório público).

O agente lê a página de saúde no primeiro comando de cada sessão: título de
issue escrito por qualquer pessoa chegaria ao contexto dele como pendência.
"""

from __future__ import annotations

import pytest

from app.collectors.sistema import _de_quem_manda


@pytest.mark.parametrize(
    "item, mostra",
    [
        ({"author_association": "OWNER"}, True),
        ({"author_association": "COLLABORATOR"}, True),
        ({"author_association": "NONE", "user": {"type": "Bot"}}, True),
        ({"author_association": "NONE", "user": {"type": "User"}}, False),
        ({"author_association": "CONTRIBUTOR", "user": {"type": "User"}}, False),
        ({}, False),
    ],
)
def test_so_quem_manda_entra_na_saude(item: dict, mostra: bool) -> None:
    assert _de_quem_manda(item) is mostra
