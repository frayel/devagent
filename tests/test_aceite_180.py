"""Aceite da spec 180: o rodapé avisa que os dados podem conter erros.

Sem internet. O `TestClient` não entra no `lifespan` (não é usado como
gerenciador de contexto), então os coletores não rodam; o calendário e o
seletor de datas são fixados como em `tests/test_aceite_173.py`.
"""

from __future__ import annotations

import re
from datetime import date

import pytest
from fastapi.testclient import TestClient

from devagent.aceite import exigir_spec_done

AVISO_LEGAL = (
    "Conteúdo informativo gerado automaticamente. "
    "Não constitui recomendação de investimento."
)
AVISO_DADOS = (
    '<p class="aviso-dados">Os números vêm de fontes gratuitas e podem conter '
    "erros ou atrasos. Confira na fonte antes de decidir.</p>"
)
PAGINAS = ["/", "/mare", "/sistema", "/consultor", "/novidades"]


def test_aceite_180_spec_done():
    exigir_spec_done("180")


@pytest.fixture(autouse=True)
def ambiente(monkeypatch):
    class Mercado:
        def mercado_aberto(self, dt):
            return False

        def pregao_corrente(self, dt):
            return date(2026, 10, 6)

        def ultimo_pregao_fechado(self, dt):
            return date(2026, 10, 6)

    monkeypatch.setattr("app.main.calendario", Mercado())
    monkeypatch.setattr(
        "app.main.obter_pregoes_disponiveis", lambda *a, **k: ["2026-10-06"]
    )
    monkeypatch.delenv("CONSULTOR_SENHA", raising=False)


def _get(caminho: str) -> str:
    from app.main import app

    resposta = TestClient(app).get(caminho)
    assert resposta.status_code == 200, caminho
    return resposta.text


def _rodape(html: str) -> str:
    achado = re.search(r"<footer>(.*?)</footer>", html, re.S)
    assert achado, "página sem <footer>"
    return achado.group(1)


@pytest.mark.parametrize("rota", PAGINAS)
def test_rodape_traz_o_aviso_de_dados_depois_do_aviso_legal(rota):
    html = _get(rota)
    assert html.count(AVISO_DADOS) == 1
    assert html.count(AVISO_LEGAL) == 1
    rodape = _rodape(html)
    assert AVISO_DADOS in rodape
    assert AVISO_LEGAL in rodape
    assert rodape.index(AVISO_LEGAL) < rodape.index(AVISO_DADOS)


@pytest.mark.parametrize("rota", ["/", "/novidades"])
def test_link_de_novidades_segue_antes_dos_avisos(rota):
    rodape = _rodape(_get(rota))
    if 'class="rodape-novidades"' in rodape:
        assert rodape.index("rodape-novidades") < rodape.index(AVISO_LEGAL)


def test_fragmento_da_mare_nao_traz_o_aviso_de_dados():
    assert "aviso-dados" not in _get("/mare/card")
