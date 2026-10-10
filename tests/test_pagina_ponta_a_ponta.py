"""A página inteira, alimentada pelos coletores de verdade.

Os testes de coletor conferem o JSON que vai para o banco; os de página
costumam usar dados escritos à mão ou o banco vazio. O elo entre os dois (o
nome de cada campo que o coletor grava e o template lê) ficava sem teste, e foi
por ali que o Radar de Faca Caindo derrubou a página em produção: o coletor
gravava `variacao_acumulada` e o template lia `retorno_acumulado`.

Aqui todos os coletores do agendador rodam contra um Yahoo falso
(`tests/yahoo_falso.py`), gravam no banco como em produção, e a página é
renderizada com o indefinido estrito do `conftest.py`. Campo com nome errado
em qualquer painel faz este teste falhar.
"""

from fastapi.testclient import TestClient

from app import agendador
from app.main import app
from tests import yahoo_falso


def _coletar_tudo(monkeypatch) -> None:
    yahoo_falso.instalar(monkeypatch)
    agendador.coletar_tudo()
    assert agendador.estado["ultimo_erro"] is None, agendador.estado["ultimo_erro"]


def test_todo_painel_recebe_dados_do_seu_coletor(monkeypatch):
    _coletar_tudo(monkeypatch)
    paineis = TestClient(app).get("/api/snapshot").json()["paineis"]
    vazios = sorted(nome for nome, dados in paineis.items() if not dados)
    assert not vazios, (
        f"Painéis sem dados com o Yahoo falso: {vazios}. Se um coletor novo "
        "usa outra rota ou outro formato, ensine tests/yahoo_falso.py a "
        "responder, para que o painel entre na renderização ponta a ponta."
    )


def test_pagina_renderiza_com_dados_reais_dos_coletores(monkeypatch):
    _coletar_tudo(monkeypatch)
    resposta = TestClient(app).get("/")
    assert resposta.status_code == 200
    #     assert "Dado indisponível agora" not in resposta.text


def test_faca_caindo_mostra_dias_e_variacao(monkeypatch):
    _coletar_tudo(monkeypatch)
    html = TestClient(app).get("/").text
    painel = html[html.index("Radar de Faca Caindo") :]
    painel = painel[: painel.index("Atrasadas do Rally")]
    assert "Nenhuma sequência de quedas detectada" not in painel
    assert " dias</span>" in painel
    assert "%" in painel and "," in painel  # variação em formato brasileiro
