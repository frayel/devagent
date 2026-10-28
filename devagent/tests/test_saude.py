import urllib.error

import pytest

from devagent import saude

PAGINA = {
    "parcial": False,
    "geral": {
        "nivel": "problema",
        "pendentes": [
            {
                "nivel": "problema",
                "grupo": "Fluxo",
                "nome": "Disparo das rodadas",
                "resumo": "último há 45 min",
                "detalhe": "O relógio externo parou.",
                "link": "https://exemplo/run/1",
            },
            {
                "nivel": "atencao",
                "grupo": "Coleta",
                "nome": "Painéis sem dados",
                "resumo": "2",
            },
        ],
    },
}


@pytest.fixture(autouse=True)
def _config(monkeypatch):
    monkeypatch.setitem(
        saude.CONFIG, "saude", {"caminho": "/api/saude", "usuario": "u"}
    )
    monkeypatch.setenv("PRODUCTION_URL", "https://produto.exemplo/")


def test_url_junta_base_e_caminho(monkeypatch):
    assert saude.url() == "https://produto.exemplo/api/saude"
    monkeypatch.setitem(saude.CONFIG, "saude", {"caminho": ""})
    with pytest.raises(saude.Indisponivel):
        saude.url()


def test_senha_vira_http_basic(monkeypatch):
    monkeypatch.setenv("SAUDE_SENHA", "s")
    pedido = saude._pedido("https://produto.exemplo/api/saude")
    assert pedido.get_header("Authorization") == "Basic dTpz"  # u:s


def test_espera_a_leitura_completa():
    respostas = [{"parcial": True, "geral": {}}, PAGINA]
    dormidas = []
    dados = saude.ler(
        espera=60, baixar=lambda _u: respostas.pop(0), dormir=dormidas.append
    )
    assert dados is PAGINA and dormidas == [10]


def test_sem_resposta_completa_devolve_a_parcial_e_fora_do_ar_falha():
    parcial = {"parcial": True, "geral": {"pendentes": []}}
    assert (
        saude.ler(espera=0, baixar=lambda _u: parcial, dormir=lambda _s: None)
        is parcial
    )

    def fora(_u):
        raise urllib.error.URLError("recusado")

    with pytest.raises(saude.Indisponivel, match="recusado"):
        saude.ler(espera=0, baixar=fora, dormir=lambda _s: None)


def test_sem_senha_nao_insiste():
    chamadas = []

    def negado(endereco):
        chamadas.append(endereco)
        raise urllib.error.HTTPError(endereco, 401, "x", {}, None)

    with pytest.raises(saude.Indisponivel, match="SAUDE_SENHA"):
        saude.ler(espera=60, baixar=negado, dormir=lambda _s: None)
    assert len(chamadas) == 1


def test_resumo_e_issue_listam_problemas_e_atencoes():
    texto = saude.resumo(PAGINA)
    assert "1 problema(s), 1 atenção(ões)" in texto
    assert "PROBLEMA  Fluxo · Disparo das rodadas" in texto
    corpo = saude.corpo_da_issue(PAGINA, "https://produto.exemplo/api/saude")
    assert "## Problemas" in corpo and "## Atenções" in corpo
    assert f"<!-- saude: {saude.chave(PAGINA)} -->" in corpo


def test_chave_muda_com_os_problemas_e_nao_com_o_texto():
    outro_texto = {
        "geral": {
            "pendentes": [
                {**PAGINA["geral"]["pendentes"][0], "resumo": "último há 50 min"}
            ]
        }
    }
    assert saude.chave(outro_texto) == saude.chave(PAGINA)
    sem_problema = {"geral": {"pendentes": [PAGINA["geral"]["pendentes"][1]]}}
    assert saude.chave(sem_problema) == ""


def test_main_sai_com_1_quando_ha_problema(monkeypatch, capsys):
    monkeypatch.setattr(saude, "ler", lambda espera: PAGINA)
    assert saude.main([]) == 1
    monkeypatch.setattr(saude, "ler", lambda espera: {"geral": {"pendentes": []}})
    assert saude.main([]) == 0

    def fora(espera):
        raise saude.Indisponivel("x")

    monkeypatch.setattr(saude, "ler", fora)
    assert saude.main([]) == 3


def test_item_em_atencao_ha_mais_de_24h_vira_problema():
    from datetime import datetime, timezone, timedelta

    agora = datetime.now(timezone.utc)
    antigo = (agora - timedelta(hours=25)).isoformat()
    recente = (agora - timedelta(hours=23)).isoformat()

    dados = {
        "geral": {
            "pendentes": [
                {"nivel": "atencao", "grupo": "A", "nome": "1", "desde": antigo},
                {"nivel": "atencao", "grupo": "A", "nome": "2", "desde": recente},
                {"nivel": "atencao", "grupo": "A", "nome": "3"},
            ]
        }
    }

    problemas = saude.pendentes(dados, "problema")
    assert len(problemas) == 1
    assert problemas[0]["nome"] == "1"

    atencoes = saude.pendentes(dados, "atencao")
    assert len(atencoes) == 2
    assert atencoes[0]["nome"] == "2"
    assert atencoes[1]["nome"] == "3"
