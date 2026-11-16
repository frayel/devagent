"""Aceite da spec 157: o Consultor lê os canais públicos do Telegram.

Sem internet: o HTTP é do `respx`, com páginas reais do `t.me` salvas em
`tests/fixtures/telegram/` (prévia do Clube Acionista, post e widget do
Repositório de Ações, widget de um ID que não existe). As pausas entre
requisições são anuladas para o teste não esperar.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from app.collectors import consultor_opinioes as coletor
from app.collectors import registro_fontes
from app.consultor.armazenamento import (
    get_connection,
    get_telegram_cursor,
    init_db,
    set_telegram_cursor,
)
from devagent.aceite import exigir_spec_done

FIXTURES = Path(__file__).parent / "fixtures" / "telegram"
PREVIA = (FIXTURES / "previa_clubeacionista.html").read_text("utf-8")
POST_REPO = (FIXTURES / "post_repositoriodeacoes.html").read_text("utf-8")
WIDGET_REPO = (FIXTURES / "widget_repositoriodeacoes.html").read_text("utf-8")
WIDGET_VAZIO = (FIXTURES / "widget_inexistente.html").read_text("utf-8")
IDS_PREVIA = list(range(60188, 60208))
AUTH = {"Authorization": "Basic Y29uc3VsdG9yOjEyMw=="}


@pytest.fixture(autouse=True)
def _limpo(monkeypatch):
    monkeypatch.setattr(coletor.time, "sleep", lambda s: None)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    registro_fontes.limpar()
    coletor.limpar_status_fontes()
    init_db()
    conn, _ = get_connection()
    c = conn.cursor()
    for tabela in (
        "consultor_fila_materias",
        "consultor_opinioes",
        "consultor_telegram_cursor",
    ):
        c.execute(f"DELETE FROM {tabela}")
    conn.commit()
    conn.close()
    yield
    registro_fontes.limpar()
    coletor.limpar_status_fontes()


def _fila() -> list[str]:
    conn, _ = get_connection()
    c = conn.cursor()
    c.execute("SELECT guid FROM consultor_fila_materias ORDER BY guid")
    guids = [r[0] for r in c.fetchall()]
    conn.close()
    return guids


def test_aceite_157_spec_done():
    exigir_spec_done("157")


def test_previa_gera_20_materias_no_formato_da_spec():
    materias = coletor.parse_previa_telegram(PREVIA)
    assert [m["id"] for m in materias] == IDS_PREVIA
    for m in materias:
        assert m["guid"] == m["link"] == f"https://t.me/clubeacionista/{m['id']}"
        assert re.fullmatch(
            r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\+00:00", m["data_publicacao"]
        )
        assert "<" not in m["conteudo"] and ">" not in m["conteudo"]
        assert m["descricao"] == ""
        assert len(m["titulo"]) <= 200
    primeira = materias[0]
    assert primeira["conteudo"] == (
        "🔔 BB Investimentos mantém Compra em ENEV3 e vê potencial de 27,8% até 2027"
    )
    assert primeira["data_publicacao"] == "2026-11-13T19:45:08+00:00"


def _so_clube(mock: respx.MockRouter) -> None:
    mock.get(url__regex=r"https://t\.me/s/clubeacionista.*").mock(
        return_value=httpx.Response(200, text=PREVIA)
    )


def test_clube_acionista_cursor_e_segunda_rodada():
    with respx.mock(assert_all_called=False) as mock:
        _so_clube(mock)
        assert coletor.coletar_canal("clubeacionista") is True
        fila = _fila()
        # As que citam ativo com opinião passam pelo filtro e vão para a fila.
        assert "https://t.me/clubeacionista/60188" in fila
        assert "https://t.me/clubeacionista/60201" in fila
        assert "https://t.me/clubeacionista/60193" not in fila
        assert get_telegram_cursor("clubeacionista") == 60207

        # Segunda rodada, mesmo HTML: nada novo, cursor parado.
        conn, _ = get_connection()
        conn.cursor().execute("DELETE FROM consultor_fila_materias")
        conn.commit()
        conn.close()
        assert coletor.coletar_canal("clubeacionista") is True
        assert _fila() == []
        assert get_telegram_cursor("clubeacionista") == 60207


def test_clube_acionista_pagina_com_before_ate_o_cursor():
    set_telegram_cursor("clubeacionista", 60100)
    with respx.mock(assert_all_called=False) as mock:
        rota = mock.get(url__regex=r"https://t\.me/s/clubeacionista.*").mock(
            return_value=httpx.Response(200, text=PREVIA)
        )
        coletor.coletar_canal("clubeacionista")
        # O cursor está longe: lê a página e segue com `before`, até 5 páginas.
        assert rota.call_count == coletor.TELEGRAM_MAX_PAGINAS
        assert "before=60188" in str(rota.calls[1].request.url)


def test_cursor_avanca_mesmo_sem_nada_passar_no_filtro():
    sem_opiniao = re.sub(
        r'(<div class="tgme_widget_message_text[^"]*"[^>]*>).*?(</div>)',
        r"\1Bom dia a todos\2",
        PREVIA,
        flags=re.S,
    )
    with respx.mock(assert_all_called=False) as mock:
        mock.get(url__regex=r"https://t\.me/s/clubeacionista.*").mock(
            return_value=httpx.Response(200, text=sem_opiniao)
        )
        coletor.coletar_canal("clubeacionista")
    assert _fila() == []
    assert get_telegram_cursor("clubeacionista") == 60207


def _repo(mock: respx.MockRouter, publicados: range) -> respx.Route:
    def widget(request: httpx.Request) -> httpx.Response:
        msg_id = int(request.url.path.rsplit("/", 1)[1])
        return httpx.Response(
            200, text=WIDGET_REPO if msg_id in publicados else WIDGET_VAZIO
        )

    rota_widget = mock.get(
        url__regex=r"https://t\.me/RepositorioDeAcoes/\d+\?embed=1"
    ).mock(side_effect=widget)
    mock.get(url__regex=r"https://t\.me/RepositorioDeAcoes/\d+$").mock(
        return_value=httpx.Response(200, text=POST_REPO)
    )
    return rota_widget


def test_repositorio_le_por_id_e_para_em_3_vazios(caplog):
    set_telegram_cursor("RepositorioDeAcoes", 159281)
    with respx.mock(assert_all_called=False) as mock:
        rota = _repo(mock, range(159282, 159291))
        materias, ok = coletor._ler_por_id("RepositorioDeAcoes", 159281)
    assert ok
    assert [m["id"] for m in materias] == list(range(159282, 159291))
    # 9 publicados + 3 vazios (159291 a 159293) e para.
    assert rota.call_count == 12
    m = materias[0]
    assert m["guid"] == "https://t.me/RepositorioDeAcoes/159282"
    assert m["titulo"] == (
        "FERREIRA GOMES ENERGIA S.A. - ITR - Informações Trimestrais (04/11/2026)"
    )
    assert m["data_publicacao"] == "2026-11-04T21:08:43+00:00"
    assert "159293" in caplog.text

    with respx.mock(assert_all_called=False) as mock:
        _repo(mock, range(159282, 159291))
        coletor.coletar_canal("RepositorioDeAcoes")
    # O filtro descarta o ITR, mas o cursor avança.
    assert _fila() == []
    assert get_telegram_cursor("RepositorioDeAcoes") == 159290


def test_repositorio_respeita_teto_de_30_ids():
    with respx.mock(assert_all_called=False) as mock:
        rota = _repo(mock, range(0, 10**7))
        materias, ok = coletor._ler_por_id("RepositorioDeAcoes", None)
    assert ok
    assert rota.call_count == coletor.TELEGRAM_MAX_IDS
    inicio = coletor.TELEGRAM_INICIO["RepositorioDeAcoes"]
    assert [m["id"] for m in materias] == list(range(inicio + 1, inicio + 31))


@pytest.mark.parametrize(
    "casa",
    [
        "Clube Acionista",
        "Repositório de Ações",
        "Universo Antifrágil",
        "repositorio de acoes",
        "Clube Acionista ",
        "UNIVERSO ANTIFRAGIL",
    ],
)
def test_opiniao_atribuida_ao_canal_e_descartada(monkeypatch, casa):
    _extrair_com(monkeypatch, casa)
    conn, _ = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM consultor_opinioes")
    assert c.fetchone()[0] == 0
    conn.close()


def _extrair_com(monkeypatch, casa: str) -> None:
    from app.consultor.armazenamento import save_materia
    from app.services import consultor_opinioes as servico

    texto = (
        "🔔 RADL3 - Ativa Investimentos recomenda COMPRA para Raia Drogasil, "
        "com preço-alvo de R$ 32,00"
    )
    save_materia(
        "https://t.me/clubeacionista/41230",
        texto,
        "",
        texto,
        "2026-11-04T13:05:00+00:00",
        "https://t.me/clubeacionista/41230",
        ["RADL3"],
    )
    resposta = [
        {
            "id_materia": "https://t.me/clubeacionista/41230",
            "ticker": "RADL3",
            "casa": casa,
            "recomendacao": "compra",
            "preco_alvo": "32,00",
            "resumo": "Compra",
            "trecho": "Ativa Investimentos recomenda COMPRA",
        }
    ]
    corpo = {"candidates": [{"content": {"parts": [{"text": json.dumps(resposta)}]}}]}
    monkeypatch.setenv("GEMINI_API_KEY", "fake")
    monkeypatch.setattr(
        servico.httpx, "post", lambda *a, **k: httpx.Response(200, json=corpo)
    )
    servico.extrair_opinioes()


def test_exemplo_de_ponta_a_ponta_na_tela(monkeypatch):
    _extrair_com(monkeypatch, "Ativa Investimentos")
    conn, _ = get_connection()
    c = conn.cursor()
    c.execute("SELECT casa, link FROM consultor_opinioes")
    assert [tuple(r) for r in c.fetchall()] == [
        ("Ativa Investimentos", "https://t.me/clubeacionista/41230")
    ]
    conn.close()

    monkeypatch.setenv("CONSULTOR_SENHA", "123")
    import app.main
    from app.consultor import regras
    from app.consultor.armazenamento import get_opinioes_recentes, ler_data
    from app.consultor.sintese import agrupar_por_ativo

    # Sem séries de mercado no banco de teste: o cálculo técnico vem pronto,
    # e as opiniões são as gravadas de verdade pela extração acima.
    # A lista da tela é por ativo (spec 165); a referência é a opinião mais
    # nova, para o teste não depender do dia em que roda.
    def calculo(ignorar_cache: bool = False) -> dict:
        opinioes = get_opinioes_recentes()
        referencia = max(ler_data(op["data_materia"]) for op in opinioes)
        return {
            "resultados": {
                g: []
                for g in ("Comprar", "Vender", "Aguardar", "No radar", "Sem sinal")
            },
            "opinioes_recentes": opinioes,
            "opinioes_por_ativo": agrupar_por_ativo(opinioes, referencia=referencia),
            "opinioes_status": {"status": "ok", "motivo": "", "desde": ""},
            "ativos_avaliados": 0,
            "regras_limiares": {
                nome: getattr(regras, nome)
                for nome in (
                    "R1_QUEDAS",
                    "R1_GATILHO_VOL",
                    "R3_IFR_MAX",
                    "R3_IFR_RECUO",
                    "R4_DISTANCIA_MM200",
                    "R4_GATILHO_VOL",
                    "R5_IFR_MIN",
                    "R5_IFR_MAX",
                )
            },
        }

    monkeypatch.setattr(app.main, "calcular_consultor", calculo)
    html = TestClient(app.main.app).get("/consultor", headers=AUTH).text
    assert "<th>Via</th>" in html
    assert "Telegram · Clube Acionista" in html
    assert 'href="https://t.me/clubeacionista/41230"' in html


def test_origem_do_link():
    assert coletor.origem_do_link("https://www.moneytimes.com.br/x/") == "Money Times"
    assert coletor.origem_do_link("https://www.infomoney.com.br/x/") == "InfoMoney"
    assert (
        coletor.origem_do_link("https://t.me/RepositorioDeAcoes/1")
        == "Telegram · Repositório de Ações"
    )
    assert coletor.origem_do_link("https://exemplo.com.br/a") == "exemplo.com.br"


def _rss() -> str:
    return (
        '<?xml version="1.0"?><rss><channel><item><title>Itaú BBA recomenda '
        "compra de PETR4</title><link>https://www.moneytimes.com.br/a/</link>"
        "<guid>https://www.moneytimes.com.br/a/</guid><description>d</description>"
        "<pubDate>Mon, 02 Nov 2026 10:00:00 +0000</pubDate></item></channel></rss>"
    )


def _api_feeds() -> list[dict]:
    from app.main import app

    resp = TestClient(app).get("/api/consultor", headers=AUTH)
    assert resp.status_code == 200
    return resp.json()["fontes_opiniao"]["feeds"]


def test_telegram_fora_do_ar_nao_derruba_os_feeds(monkeypatch):
    monkeypatch.setenv("CONSULTOR_SENHA", "123")
    feeds = _api_feeds()
    assert len(feeds) == 5
    assert {f["status"] for f in feeds} == {"sem coleta"}
    assert {f["ultima_coleta"] for f in feeds} == {""}
    assert {f["url"] for f in feeds} >= {
        "https://t.me/clubeacionista",
        "https://t.me/RepositorioDeAcoes",
        "https://t.me/universoantifragil",
    }

    set_telegram_cursor("RepositorioDeAcoes", 159281)
    with respx.mock(assert_all_called=False) as mock:
        mock.get(url__regex=r"https://www\.(moneytimes|infomoney)\.com\.br/feed/").mock(
            return_value=httpx.Response(200, text=_rss())
        )
        mock.get(url__regex=r"https://t\.me/.*").mock(
            return_value=httpx.Response(500, text="erro")
        )
        coletor.collect_and_save()  # não levanta

    assert "https://www.moneytimes.com.br/a/" in _fila()
    assert get_telegram_cursor("RepositorioDeAcoes") == 159281
    assert get_telegram_cursor("clubeacionista") is None

    registro = registro_fontes.fontes()
    assert registro["Telegram"].falhas > 0 and registro["Telegram"].sucessos == 0
    assert registro["Money Times"].sucessos > 0
    assert registro["InfoMoney"].sucessos > 0

    por_url = {f["url"]: f for f in _api_feeds()}
    for canal in coletor.TELEGRAM_CANAIS:
        assert por_url[f"https://t.me/{canal}"]["status"] == "falha"
        assert por_url[f"https://t.me/{canal}"]["ultima_coleta"]
    for url in coletor.FEEDS:
        assert por_url[url]["status"] == "ok"
        assert por_url[url]["ultima_coleta"]
