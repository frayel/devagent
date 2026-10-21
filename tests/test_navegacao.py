"""Cabeçalho comum: todas as páginas levam de volta aos painéis e marcam a aba atual."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client(monkeypatch):
    monkeypatch.delenv("CONSULTOR_SENHA", raising=False)
    return TestClient(app)


@pytest.mark.parametrize("caminho", ["/", "/consultor", "/sistema"])
def test_cabecalho_tem_link_para_os_paineis(client, caminho):
    html = client.get(caminho).text
    assert '<a href="/" class="marca">' in html
    assert 'href="/" class="menu-link' in html
    assert ">Painéis</a>" in html


@pytest.mark.parametrize(
    "caminho,rotulo",
    [("/", "Painéis"), ("/consultor", "Consultor"), ("/sistema", "Sistema")],
)
def test_aba_atual_marcada(client, caminho, rotulo):
    html = client.get(caminho).text
    assert (
        f'href="{caminho}" class="menu-link ativo" aria-current="page">{rotulo}</a>'
        in html
    )
    assert html.count('aria-current="page"') == 1
