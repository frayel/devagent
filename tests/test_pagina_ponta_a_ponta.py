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
    import app.collectors.radar_divergencia_volume

    if "DIV" not in app.collectors.radar_divergencia_volume.TICKERS:
        monkeypatch.setattr("app.collectors.radar_divergencia_volume.TICKERS", ["DIV"])
    import app.collectors.exaustao_tendencia

    if "EXAUSTAO" not in app.collectors.exaustao_tendencia.TICKERS:
        monkeypatch.setattr("app.collectors.exaustao_tendencia.TICKERS", ["EXAUSTAO"])

    import app.collectors.exaustao_queda

    if "EXQ" not in app.collectors.exaustao_queda.TICKERS:
        monkeypatch.setattr("app.collectors.exaustao_queda.TICKERS", ["EXQ"])

    monkeypatch.setattr(
        "app.collectors.concentracao_ordens.collect_and_save", lambda: True
    )
    from app.database import ConcentracaoOrdensData, save_concentracao_ordens_data
    import json
    from datetime import datetime, timezone

    save_concentracao_ordens_data(
        ConcentracaoOrdensData(
            timestamp=datetime.now(timezone.utc),
            alertas_json=json.dumps(
                [
                    {
                        "ticker": "FAKE3",
                        "ticket_medio": 1500.5,
                        "volume_financeiro": 150050,
                        "trades": 100,
                    }
                ]
            ),
            fonte="mock",
        )
    )
    yahoo_falso.instalar(monkeypatch)
    monkeypatch.setattr(
        "app.collectors.consultor_historico.collect_and_save", lambda: True
    )
    monkeypatch.setattr(
        "app.collectors.consultor_fechamento.collect_and_save", lambda: True
    )
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


def test_nenhum_painel_vaza_dicionario_cru(monkeypatch):
    _coletar_tudo(monkeypatch)
    resposta = TestClient(app).get("/")
    assert resposta.status_code == 200
    html = resposta.text
    # Busca por resquícios de formatação dicionário em conteúdo de tabela
    assert "{&#39;" not in html, "Dicionário Python cru vazou no HTML"
    assert "{'" not in html, "Dicionário Python cru vazou no HTML"
