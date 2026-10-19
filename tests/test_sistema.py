"""Página de sistema (spec 082): níveis, cron, registro das fontes e rotas."""

from datetime import datetime, timedelta, timezone

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from app.collectors import registro_fontes
from app.collectors import sistema as monitor
from app.collectors.utils import fetch_with_retry
from app.main import app as fastapi_app
from app.services import sistema as s
from app.services.cron import Cron

AGORA = datetime(2026, 10, 19, 15, 0, tzinfo=timezone.utc)  # segunda, 12h BRT
client = TestClient(fastapi_app)


def iso(delta: timedelta) -> str:
    return (AGORA - delta).isoformat().replace("+00:00", "Z")


@pytest.fixture(autouse=True)
def _limpo(monkeypatch):
    registro_fontes.limpar()
    for chave in list(monitor.retrato):
        monitor.retrato[chave] = None
    monkeypatch.setattr(monitor, "_enforce_rate_limit", lambda _d: None)
    yield
    registro_fontes.limpar()


# --------------------------------------------------------------------------
# Cron
# --------------------------------------------------------------------------


def test_cron_do_pregao_dispara_nos_minutos_e_horas_certos():
    cron = Cron("7,37 13-21 * * 1-5")
    disparos = cron.disparos(
        datetime(2026, 10, 19, 12, 0, tzinfo=timezone.utc),
        datetime(2026, 10, 19, 14, 0, tzinfo=timezone.utc),
    )
    assert [d.strftime("%H:%M") for d in disparos] == ["13:07", "13:37"]


def test_cron_dia_da_semana_respeita_domingo_como_0_e_7():
    sabado = datetime(2026, 10, 17, 14, 41, tzinfo=timezone.utc)
    domingo = datetime(2026, 10, 18, 14, 41, tzinfo=timezone.utc)
    segunda = datetime(2026, 10, 19, 14, 41, tzinfo=timezone.utc)
    fim_de_semana = Cron("41 14 * * 0,6")
    assert fim_de_semana.casa(sabado) and fim_de_semana.casa(domingo)
    assert not fim_de_semana.casa(segunda)
    assert Cron("41 14 * * 7").casa(domingo)


def test_cron_com_passo_e_invalido():
    assert Cron("17 */6 * * *").casa(datetime(2026, 1, 1, 18, 17))
    assert not Cron("17 */6 * * *").casa(datetime(2026, 1, 1, 19, 17))
    with pytest.raises(ValueError):
        Cron("61 * * * *")
    with pytest.raises(ValueError):
        Cron("* * *")


def test_disparos_perdidos_desconta_a_hora_de_folga():
    crons = ["53 * * * *"]
    agendado = {"criado_em": iso(timedelta(hours=4, minutes=30))}  # 10:30 UTC
    # Esperados 10:53, 11:53, 12:53, 13:53; 14:53 ainda está na folga de 1 h.
    assert s.disparos_perdidos(crons, agendado, AGORA) == 4
    recente = {"criado_em": iso(timedelta(minutes=50))}
    assert s.disparos_perdidos(crons, recente, AGORA) == 0


def test_workflows_do_repositorio_le_os_crons_dos_arquivos():
    workflows = {w["arquivo"]: w for w in monitor.workflows_do_repositorio()}
    assert workflows["jules.yml"]["crons"] == []
    assert len(workflows["auditoria-producao.yml"]["crons"]) == 3
    assert workflows["ci.yml"]["nome"] == "CI"


# --------------------------------------------------------------------------
# Integrações (registro das fontes)
# --------------------------------------------------------------------------


@respx.mock
def test_fetch_with_retry_registra_sucesso_e_falha():
    respx.get("https://brapi.dev/api/quote/PETR4?token=abc").mock(
        return_value=httpx.Response(200, json={})
    )
    respx.get("https://brapi.dev/api/quote/VALE3?token=abc").mock(
        return_value=httpx.Response(404)
    )
    fetch_with_retry("https://brapi.dev/api/quote/PETR4?token=abc")
    with pytest.raises(httpx.HTTPStatusError):
        fetch_with_retry("https://brapi.dev/api/quote/VALE3?token=abc")
    brapi = registro_fontes.fontes()["brapi"]
    assert (brapi.sucessos, brapi.falhas) == (1, 1)
    assert brapi.ultimo_erro.startswith("HTTP 404 em")


def test_registro_mascara_segredo_no_erro():
    registro_fontes.falha("brapi", "falhou em https://brapi.dev/x?token=segredo123")
    assert "segredo123" not in (registro_fontes.fontes()["brapi"].ultimo_erro or "")


def _fonte(resultados: list[bool]) -> registro_fontes.Fonte:
    f = registro_fontes.Fonte("Yahoo Finance")
    f.recentes = resultados
    f.sucessos = resultados.count(True)
    f.falhas = resultados.count(False)
    f.ultimo_sucesso = AGORA - timedelta(minutes=5) if True in resultados else None
    f.ultima_falha = AGORA - timedelta(minutes=1) if False in resultados else None
    f.ultimo_erro = "HTTP 429" if False in resultados else None
    return f


@pytest.mark.parametrize(
    ("resultados", "nivel"),
    [
        ([True] * 10, s.OK),
        ([True] * 9 + [False], s.ATENCAO),
        ([True] * 5 + [False] * 5, s.PROBLEMA),
        ([True, False, True, False, True], s.ATENCAO),
    ],
)
def test_nivel_da_integracao_pelas_chamadas_recentes(resultados, nivel):
    itens = s.verificar_integracoes(
        {"Yahoo Finance": _fonte(resultados)}, None, {}, AGORA
    )
    yahoo = next(i for i in itens if i.nome == "Yahoo Finance")
    assert yahoo.nivel == nivel


def test_integracao_sem_configuracao_fica_inativa_e_mt5_em_pausa_e_problema():
    itens = {i.nome: i for i in s.verificar_integracoes({}, None, {}, AGORA)}
    assert itens["MetaTrader 5"].nivel == s.INATIVO
    assert itens["Gemini"].resumo == "sem GEMINI_API_KEY"
    ambiente = {"MT5_API_URL": "http://host:8000"}
    pausa = (240.0, "ConnectError ao conectar")
    itens = {i.nome: i for i in s.verificar_integracoes({}, pausa, ambiente, AGORA)}
    assert itens["MetaTrader 5"].nivel == s.PROBLEMA
    assert "ConnectError" in itens["MetaTrader 5"].detalhe


# --------------------------------------------------------------------------
# Aplicação, banco e coleta
# --------------------------------------------------------------------------


def _github(**extra):
    base = {
        "main": {
            "sha": "b" * 40,
            "data": iso(timedelta(minutes=5)),
            "mensagem": "feat: x",
            "url": "u",
        },
        "producao": {
            "sha": "a" * 40,
            "data": iso(timedelta(hours=3)),
            "mensagem": "feat: y",
            "atras": 2,
        },
        "runs": [],
        "workflows": [],
        "prs": [],
        "issues": [],
        "ultimo_agendado": {},
        "limite": {"restante": 4999, "total": 5000},
        "com_token": True,
    }
    base.update(extra)
    return base


def test_deploy_atrasado_vira_problema_depois_de_uma_hora():
    recente = _github()
    itens = {i.nome: i for i in s.verificar_versao(recente, None, AGORA)}
    assert itens["Deploy"].nivel == s.OK
    assert "em andamento" in itens["Deploy"].resumo

    velho = _github()
    velho["main"]["data"] = iso(timedelta(hours=2))
    itens = {i.nome: i for i in s.verificar_versao(velho, None, AGORA)}
    assert itens["Deploy"].nivel == s.PROBLEMA
    assert "2 commits" in itens["Deploy"].resumo


def test_banco_sqlite_com_database_url_pede_atencao():
    info = {"tipo": "SQLite", "tamanho": "1 MB", "latencia_ms": 2, "tabelas": 40}
    assert s.verificar_banco({**info, "database_url": False}).nivel == s.OK
    assert s.verificar_banco({**info, "database_url": True}).nivel == s.ATENCAO
    assert s.verificar_banco({"tipo": "SQLite", "erro": "x"}).nivel == s.PROBLEMA


def test_agendador_atrasado():
    quinze = timedelta(minutes=15)
    inicio = AGORA - timedelta(hours=5)
    em_dia = {"ultima_coleta": (AGORA - timedelta(minutes=10)).isoformat()}
    atrasado = {"ultima_coleta": (AGORA - timedelta(minutes=50)).isoformat()}
    parado = {"ultima_coleta": (AGORA - timedelta(hours=2)).isoformat()}
    assert s.verificar_agendador(True, em_dia, quinze, inicio, AGORA)[0].nivel == s.OK
    assert (
        s.verificar_agendador(True, atrasado, quinze, inicio, AGORA)[0].nivel
        == s.ATENCAO
    )
    assert (
        s.verificar_agendador(True, parado, quinze, inicio, AGORA)[0].nivel
        == s.PROBLEMA
    )
    desligado = s.verificar_agendador(False, {}, quinze, inicio, AGORA)
    assert desligado[0].nivel == s.INATIVO


# --------------------------------------------------------------------------
# Fluxo de desenvolvimento
# --------------------------------------------------------------------------


def _run(caminho, evento, conclusao, idade, status="completed"):
    return {
        "nome": caminho,
        "caminho": caminho,
        "evento": evento,
        "status": status,
        "conclusao": conclusao,
        "criado_em": iso(idade),
        "url": "u",
    }


def test_rodadas_do_jules_paradas_viram_problema():
    jules = ".github/workflows/jules.yml"
    em_dia = _github(
        runs=[_run(jules, "workflow_dispatch", "success", timedelta(minutes=3))]
    )
    assert s.verificar_rodadas_jules(em_dia, 5, AGORA).nivel == s.OK
    parado = _github(
        runs=[_run(jules, "workflow_dispatch", "success", timedelta(minutes=45))]
    )
    item = s.verificar_rodadas_jules(parado, 5, AGORA)
    assert item.nivel == s.PROBLEMA
    assert "cron-job.org" in item.detalhe
    falhando = _github(
        runs=[
            _run(jules, "workflow_dispatch", "failure", timedelta(minutes=m))
            for m in (2, 7, 12)
        ]
    )
    assert s.verificar_rodadas_jules(falhando, 5, AGORA).nivel == s.PROBLEMA


def test_workflow_falho_no_pr_e_atencao_e_agendado_falho_e_problema():
    ci = ".github/workflows/ci.yml"
    aud = ".github/workflows/auditoria-producao.yml"
    github = _github(
        workflows=[
            {"arquivo": "ci.yml", "caminho": ci, "nome": "CI", "crons": []},
            {
                "arquivo": "auditoria-producao.yml",
                "caminho": aud,
                "nome": "Auditoria de produção",
                "crons": ["7,37 13-21 * * 1-5"],
            },
        ],
        runs=[
            _run(ci, "pull_request", "failure", timedelta(minutes=10)),
            _run(aud, "schedule", "failure", timedelta(minutes=20)),
        ],
        ultimo_agendado={aud: _run(aud, "schedule", "failure", timedelta(minutes=20))},
    )
    itens = {i.nome: i for i in s.verificar_workflows(github, AGORA)}
    assert itens["CI"].nivel == s.ATENCAO
    assert itens["Auditoria de produção"].nivel == s.PROBLEMA


def test_agendamentos_descartados_pelo_github_pedem_atencao():
    aud = ".github/workflows/auditoria-producao.yml"
    antigo = _run(aud, "schedule", "success", timedelta(days=4))
    github = _github(
        workflows=[
            {
                "arquivo": "auditoria-producao.yml",
                "caminho": aud,
                "nome": "Auditoria de produção",
                "crons": ["7,37 13-21 * * 1-5"],
            }
        ],
        runs=[_run(aud, "workflow_dispatch", "success", timedelta(minutes=30))],
        ultimo_agendado={aud: antigo},
    )
    item = s.verificar_workflows(github, AGORA)[0]
    assert item.nivel == s.ATENCAO
    assert "agendamentos não rodaram" in item.resumo


def test_issues_e_prs_que_pedem_acao():
    github = _github(
        issues=[
            {
                "numero": 1,
                "titulo": "deploy",
                "labels": ["deploy-falhou"],
                "criado_em": "",
                "url": "",
            },
            {
                "numero": 2,
                "titulo": "ideia",
                "labels": ["enhancement"],
                "criado_em": "",
                "url": "",
            },
        ],
        prs=[
            {
                "numero": 9,
                "titulo": "feat",
                "criado_em": iso(timedelta(hours=13)),
                "url": "u",
                "autor": "x",
                "rascunho": False,
            }
        ],
    )
    issues = s.verificar_issues(github, AGORA)
    assert (
        issues.nivel == s.PROBLEMA
        and "#1" in issues.detalhe
        and "#2" not in issues.detalhe
    )
    assert s.verificar_prs(github, AGORA).nivel == s.PROBLEMA
    assert s.verificar_prs(_github(), AGORA).nivel == s.OK


def test_sessoes_do_jules_esperando_resposta():
    jules = {
        "sessoes": [
            {
                "titulo": "Desenvolvedor · ciclo",
                "estado": "AWAITING_USER_FEEDBACK",
                "criada_em": iso(timedelta(hours=1)),
                "atualizada_em": iso(timedelta(minutes=45)),
                "url": None,
            },
            {
                "titulo": "antiga",
                "estado": "COMPLETED",
                "criada_em": iso(timedelta(hours=30)),
                "atualizada_em": iso(timedelta(hours=29)),
                "url": None,
            },
        ]
    }
    item = s.verificar_sessoes_jules(jules, None, 100, AGORA)
    assert item.nivel == s.ATENCAO
    assert item.resumo == "1 ativa · 1 de 100 em 24 h"
    assert s.verificar_sessoes_jules(None, None, 0, AGORA).nivel == s.INATIVO


def test_resumo_geral_poe_problemas_primeiro():
    estado = s.montar(
        agora=AGORA,
        inicio=AGORA - timedelta(hours=1),
        remoto={"github": _github(), "atualizado_em": AGORA.isoformat()},
        sha_local=None,
        banco={
            "tipo": "SQLite",
            "database_url": True,
            "tamanho": "1 MB",
            "latencia_ms": 1,
            "tabelas": 3,
        },
        coleta_ligada=True,
        estado_coleta={"ultima_coleta": (AGORA - timedelta(minutes=5)).isoformat()},
        intervalo_coleta=timedelta(minutes=15),
        vazios={"mare": 2},
        horas_vazios=3,
        tempos={"mare": 12.0},
        fontes={},
        pausa_mt5=None,
        prontas=["082-x"],
        ambiente={},
    )
    geral = estado["geral"]
    assert geral["nivel"] == s.PROBLEMA  # jules.yml sem disparo
    niveis = [p["nivel"] for p in geral["pendentes"]]
    assert niveis == sorted(niveis, key=lambda n: -s.PESO[n])
    assert {g["titulo"] for g in estado["grupos"]} >= {
        "Aplicação e banco",
        "Coleta",
        "Integrações externas",
        "Fluxo de desenvolvimento",
    }


def test_specs_prontas_le_a_fila_do_repositorio():
    prontas = s.specs_prontas()
    assert all(not p.startswith("082") for p in prontas)


# --------------------------------------------------------------------------
# Monitor e rotas
# --------------------------------------------------------------------------


@respx.mock
def test_falha_do_github_guarda_o_erro_e_mantem_o_retrato_anterior(monkeypatch):
    monkeypatch.delenv("JULES_API_KEY", raising=False)
    monkeypatch.delenv("RENDER_API_KEY", raising=False)
    monitor.retrato["github"] = {"anterior": True}
    respx.get(url__startswith="https://api.github.com/").mock(
        return_value=httpx.Response(500)
    )
    monitor.atualizar()
    assert monitor.retrato["github"] == {"anterior": True}
    assert monitor.retrato["github_erro"] == "HTTP 500"
    assert monitor.retrato["jules"] is None and monitor.retrato["atualizado_em"]


def test_pagina_sistema_renderiza_sem_vazar_segredos(monkeypatch):
    monkeypatch.delenv("CONSULTOR_SENHA", raising=False)
    monkeypatch.setenv("MT5_API_URL", "http://10.0.0.7:8000/api/v1")
    monkeypatch.setenv("MT5_API_KEY", "chave-muito-secreta")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-secreto")
    resposta = client.get("/sistema")
    assert resposta.status_code == 200
    assert "Estado do sistema" in resposta.text
    assert "Integrações externas" in resposta.text
    for segredo in ("10.0.0.7", "chave-muito-secreta", "gemini-secreto"):
        assert segredo not in resposta.text
        assert segredo not in client.get("/api/sistema").text
    assert 'href="/sistema"' in client.get("/").text


def test_sistema_usa_a_senha_do_consultor(monkeypatch):
    monkeypatch.setenv("CONSULTOR_SENHA", "s3nha")
    assert client.get("/sistema").status_code == 401
    assert client.get("/api/sistema").status_code == 401
    assert client.get("/api/sistema", auth=("consultor", "errada")).status_code == 401
    resposta = client.get("/api/sistema", auth=("consultor", "s3nha"))
    assert resposta.status_code == 200
    assert resposta.json()["geral"]["nivel"] in {s.OK, s.ATENCAO, s.PROBLEMA}


def test_api_sistema_cumpre_o_contrato_de_saude_do_nucleo(monkeypatch):
    """devagent/saude.py (ADR 016) só lê `parcial` e `geral`."""
    monkeypatch.delenv("CONSULTOR_SENHA", raising=False)
    dados = client.get("/api/sistema").json()
    assert dados["parcial"] is False  # monitor desligado nos testes
    assert dados["geral"]["nivel"] in {s.OK, s.ATENCAO, s.PROBLEMA}
    for p in dados["geral"]["pendentes"]:
        assert {"nivel", "grupo", "nome", "resumo", "detalhe"} <= set(p)


def test_so_404_e_pedido_errado_e_nao_fonte_fora_do_ar():
    f = registro_fontes.Fonte("Yahoo Finance")
    f.recentes = [False, False, False]
    f.graves = [False, False, False]
    f.falhas = 3
    f.ultima_falha = AGORA
    f.ultimo_erro = (
        "HTTP 404 em https://query1.finance.yahoo.com/v7/finance/spark?symbols=X"
    )
    item = s.verificar_integracoes({"Yahoo Finance": f}, None, {}, AGORA)[1]
    assert item.nivel == s.ATENCAO
    assert "spark?symbols=X" in item.detalhe
    f.graves = [False, True, False]
    assert (
        s.verificar_integracoes({"Yahoo Finance": f}, None, {}, AGORA)[1].nivel
        == s.PROBLEMA
    )


def test_poucas_chamadas_nao_viram_problema():
    item = s.verificar_integracoes(
        {"Yahoo Finance": _fonte([False, False])}, None, {}, AGORA
    )[1]
    assert item.nivel == s.ATENCAO


@respx.mock
def test_registro_guarda_url_mascarada_e_gravidade():
    respx.get("https://brapi.dev/api/quote/X?token=abc").mock(
        return_value=httpx.Response(404)
    )
    with pytest.raises(httpx.HTTPStatusError):
        fetch_with_retry("https://brapi.dev/api/quote/X?token=abc")
    brapi = registro_fontes.fontes()["brapi"]
    assert brapi.ultimo_erro == "HTTP 404 em https://brapi.dev/api/quote/X?token=***"
    assert brapi.graves == [False]


def test_painel_vazio_em_todas_as_rodadas_e_problema():
    item = s.verificar_paineis_vazios(
        {"sensibilidade_juros": 4, "mare": 1}, 3, {"sensibilidade_juros": 4, "mare": 4}
    )
    assert item.nivel == s.PROBLEMA
    assert "sensibilidade_juros" in item.resumo and "mare" not in item.resumo
    oscilando = s.verificar_paineis_vazios({"mare": 1}, 3, {"mare": 4})
    assert oscilando.nivel == s.ATENCAO
