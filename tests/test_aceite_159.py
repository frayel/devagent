"""Aceite da spec 159: o Consultor mostra o consenso de analistas do Yahoo.

Sem internet: o HTTP é do `respx`. As respostas de `financialData` estão em
`tests/fixtures/yahoo/`, no formato `{"raw": ..., "fmt": ...}` do Yahoo.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from app import calendario
from app.collectors import consultor_yahoo as coletor
from app.collectors import registro_fontes
from app.consultor import armazenamento, consenso_yahoo
from app.consultor.universo import CARTEIRA_IBOVESPA
from app.services import sistema as sistema_servico
from devagent.aceite import exigir_spec_done

FIXTURES = Path(__file__).parent / "fixtures" / "yahoo"
AUTH = {"Authorization": "Basic Y29uc3VsdG9yOjEyMw=="}
GRUPOS = ("Comprar", "Vender", "Aguardar", "No radar", "Sem sinal")
FRASE = "Yahoo: compra (2,1) · 12 analistas · alvo médio R$ 15,40"


def _json(nome: str) -> dict:
    return json.loads((FIXTURES / nome).read_text("utf-8"))


@pytest.fixture(autouse=True)
def _limpo():
    registro_fontes.limpar()
    armazenamento.reset_db_init()
    armazenamento.init_db()
    conn, _ = armazenamento.get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM consultor_consenso_yahoo")
    c.execute("DELETE FROM consultor_consenso_yahoo_status")
    conn.commit()
    conn.close()
    yield
    registro_fontes.limpar()


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def _data_pagina(agora: datetime):
    """A data de referência que o `/consultor` usa sem `?data=`."""
    if calendario.mercado_aberto(agora):
        return calendario.pregao_corrente(agora)
    return calendario.ultimo_pregao_fechado(agora)


def _rotas_yahoo(mock: respx.MockRouter, por_ticker: dict[str, httpx.Response]):
    mock.get(coletor.URL_COOKIE).mock(return_value=httpx.Response(404))
    crumb = mock.get(coletor.URL_CRUMB).mock(
        return_value=httpx.Response(200, text="abcCRUMB")
    )
    padrao = httpx.Response(200, json=_json("quotesummary_sem_cobertura.json"))
    resumo = mock.get(url__regex=r"/v10/finance/quoteSummary/").mock(
        side_effect=lambda req: por_ticker.get(
            req.url.path.rsplit("/", 1)[-1].removesuffix(".SA"), padrao
        )
    )
    return crumb, resumo


def _linhas() -> list[tuple]:
    conn, _ = armazenamento.get_connection()
    c = conn.cursor()
    c.execute(
        "SELECT ticker, recomendacao_media, analistas, alvo_medio, alvo_minimo, "
        "alvo_maximo FROM consultor_consenso_yahoo ORDER BY ticker"
    )
    linhas = [tuple(r) for r in c.fetchall()]
    conn.close()
    return linhas


def _calculo(itens: dict[str, list[str]]):
    """`calcular_consultor` pronto: o banco de teste não tem séries."""
    from app.consultor import regras

    def calculo(ignorar_cache: bool = False) -> dict:
        return {
            "resultados": {
                g: [
                    {
                        "ticker": t,
                        "fechamento": 13.12,
                        "regra": "R5 Tendência de alta saudável",
                        "motivo": "m",
                        "gatilho": "-",
                        "decisao_tecnica": g,
                        "justificativa": "",
                        "mensagem_confianca": "histórico indisponível",
                        "consenso": {
                            "consenso": "cobertura insuficiente",
                            "preco_alvo_mediano": None,
                            "potencial": None,
                        },
                        "opinioes": [],
                    }
                    for t in itens.get(g, [])
                ]
                for g in GRUPOS
            },
            "opinioes_recentes": [],
            "opinioes_status": {"status": "ok", "motivo": "", "desde": ""},
            "ativos_avaliados": 1,
            "regras_limiares": {
                n: getattr(regras, n)
                for n in (
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

    return calculo


def _cliente(monkeypatch, itens: dict[str, list[str]]) -> TestClient:
    import app.main

    monkeypatch.setenv("CONSULTOR_SENHA", "123")
    monkeypatch.setattr(app.main, "calcular_consultor", _calculo(itens))
    return TestClient(app.main.app)


def _api_item(cliente: TestClient, ticker: str) -> dict:
    resp = cliente.get("/api/consultor", headers=AUTH)
    assert resp.status_code == 200
    for itens in resp.json()["resultados"].values():
        for item in itens:
            if item["ticker"] == ticker:
                return item
    raise AssertionError(f"{ticker} ausente")


def test_aceite_159_spec_done():
    exigir_spec_done("159")


@pytest.mark.parametrize(
    "media, rotulo",
    [
        (1.0, "compra forte"),
        (1.5, "compra forte"),
        (1.51, "compra"),
        (2.5, "compra"),
        (3.5, "neutro"),
        (4.5, "venda"),
        (4.51, "venda forte"),
    ],
)
def test_fronteiras_do_rotulo(media, rotulo):
    assert consenso_yahoo.rotulo(media) == rotulo


def test_fixture_grava_linha_e_tela_mostra_a_frase(monkeypatch):
    agora = _agora()
    with respx.mock(assert_all_called=False) as mock:
        _, resumo = _rotas_yahoo(
            mock,
            {"PETR4": httpx.Response(200, json=_json("quotesummary_petr4.json"))},
        )
        assert coletor.collect_and_save(agora) is True
        assert resumo.call_count == len(CARTEIRA_IBOVESPA)
        pedido = resumo.calls[0].request
        assert pedido.url.params["modules"] == "financialData"
        assert pedido.url.params["crumb"] == "abcCRUMB"

    assert _linhas() == [("PETR4", 2.1, 12, 15.4, 12.0, 19.0)]
    conn, _ = armazenamento.get_connection()
    c = conn.cursor()
    c.execute("SELECT data FROM consultor_consenso_yahoo")
    assert c.fetchone()[0] == calendario.ultimo_pregao_fechado(agora).isoformat()
    conn.close()

    cliente = _cliente(monkeypatch, {"Comprar": ["PETR4"]})
    html = cliente.get("/consultor", headers=AUTH).text
    assert FRASE in html

    api = _api_item(cliente, "PETR4")["consenso_yahoo"]
    assert api["rotulo"] == "compra"
    assert (
        api["recomendacao_media"],
        api["analistas"],
        api["alvo_medio"],
        api["alvo_minimo"],
        api["alvo_maximo"],
    ) == (2.1, 12, 15.4, 12.0, 19.0)
    assert api["data"] == calendario.ultimo_pregao_fechado(agora).isoformat()

    item = sistema_servico.verificar_consenso_yahoo(
        armazenamento.resumo_consenso_yahoo(), agora
    )
    assert item.nivel == sistema_servico.OK
    dia = calendario.ultimo_pregao_fechado(agora).strftime("%d/%m")
    assert item.resumo == f"1 de {len(CARTEIRA_IBOVESPA)} ativos em {dia}"


@pytest.mark.parametrize("onde, status", [("crumb", 401), ("ativo", 429)])
def test_bloqueio_pausa_24h_sem_gravar(monkeypatch, onde, status):
    agora = _agora()
    with respx.mock(assert_all_called=False) as mock:
        crumb, resumo = _rotas_yahoo(mock, {})
        if onde == "crumb":
            crumb.mock(
                return_value=httpx.Response(401, json=_json("crumb_invalido_401.json"))
            )
        else:
            resumo.mock(return_value=httpx.Response(429, text="Too Many Requests"))
        assert coletor.collect_and_save(agora) is True
        chamadas = len(mock.calls)
        assert resumo.call_count == (1 if onde == "ativo" else 0)

        # Dentro das 24 h, mesmo num reinício (a pausa está no banco), nada é chamado.
        assert coletor.collect_and_save(agora + timedelta(hours=23)) is True
        assert len(mock.calls) == chamadas

    assert _linhas() == []
    st = armazenamento.get_consenso_yahoo_status()
    assert st["status"] == "pausa" and st["motivo"] == f"HTTP {status}"

    cliente = _cliente(monkeypatch, {"Comprar": ["PETR4"]})
    assert _api_item(cliente, "PETR4")["consenso_yahoo"] is None

    import app.main

    estado = app.main.estado_do_sistema()
    coleta = next(g for g in estado["grupos"] if g["titulo"] == "Coleta")
    item = next(i for i in coleta["itens"] if i["nome"] == "Yahoo · consenso")
    assert item["nivel"] == "atencao"
    quando = agora.astimezone(coletor.BRT).strftime("%d/%m %H:%M")
    assert item["resumo"] == f"bloqueado (HTTP {status}) desde {quando}"

    # A integração "Yahoo Finance" (o chart) não ganha falha.
    yahoo = registro_fontes.fontes().get("Yahoo Finance")
    assert yahoo is None or yahoo.falhas == 0


def test_tres_ativos_seguidos_sem_resposta_pausam():
    agora = _agora()
    with respx.mock(assert_all_called=False) as mock:
        _, resumo = _rotas_yahoo(mock, {})
        resumo.mock(return_value=httpx.Response(503))
        coletor.collect_and_save(agora)
        assert resumo.call_count == 3
    st = armazenamento.get_consenso_yahoo_status()
    assert st["status"] == "pausa"
    assert st["motivo"] == "3 ativos seguidos sem resposta"


def test_pregao_ja_lido_nao_faz_requisicao():
    agora = _agora()
    data = calendario.ultimo_pregao_fechado(agora).isoformat()
    armazenamento.save_consenso_yahoo(
        [{"ticker": "VALE3", "recomendacao_media": 2.0, "analistas": 5}],
        data,
        agora.isoformat(),
    )
    with respx.mock(assert_all_called=False) as mock:
        _rotas_yahoo(mock, {})
        assert coletor.collect_and_save(agora) is True
        assert len(mock.calls) == 0


def test_uma_rodada_por_dia_mesmo_sem_cobertura():
    """Rodada sem nenhuma linha não repete na mesma janela de fechamento."""
    agora = _agora()
    with respx.mock(assert_all_called=False) as mock:
        _rotas_yahoo(mock, {})
        coletor.collect_and_save(agora)
        chamadas = len(mock.calls)
        coletor.collect_and_save(agora + timedelta(minutes=30))
        assert len(mock.calls) == chamadas
    assert _linhas() == []


def test_sem_cobertura_nao_grava_e_sem_alvo_omite_o_trecho(monkeypatch):
    agora = _agora()
    with respx.mock(assert_all_called=False) as mock:
        _rotas_yahoo(
            mock,
            {
                "PETR4": httpx.Response(
                    200, json=_json("quotesummary_sem_cobertura.json")
                ),
                "VALE3": httpx.Response(
                    200, json=_json("quotesummary_zero_analistas.json")
                ),
                "ITUB4": httpx.Response(200, json=_json("quotesummary_sem_alvo.json")),
            },
        )
        coletor.collect_and_save(agora)
    assert _linhas() == [("ITUB4", 1.4, 3, None, None, None)]

    cliente = _cliente(
        monkeypatch, {"Comprar": ["PETR4", "VALE3"], "Aguardar": ["ITUB4"]}
    )
    html = cliente.get("/consultor", headers=AUTH).text
    assert "Yahoo: compra forte (1,4) · 3 analistas<" in html
    assert "alvo médio" not in html
    assert html.count("Yahoo: ") == 1
    assert _api_item(cliente, "PETR4")["consenso_yahoo"] is None
    assert _api_item(cliente, "VALE3")["consenso_yahoo"] is None


def test_leitura_de_dois_pregoes_antes_nao_aparece(monkeypatch):
    agora = _agora()
    ref = _data_pagina(agora)
    antiga = calendario.pregao_anterior(calendario.pregao_anterior(ref))
    armazenamento.save_consenso_yahoo(
        [
            {
                "ticker": "PETR4",
                "recomendacao_media": 2.1,
                "analistas": 12,
                "alvo_medio": 15.4,
            }
        ],
        antiga.isoformat(),
        agora.isoformat(),
    )
    cliente = _cliente(monkeypatch, {"Comprar": ["PETR4"]})
    assert "Yahoo:" not in cliente.get("/consultor", headers=AUTH).text
    assert _api_item(cliente, "PETR4")["consenso_yahoo"] is None

    # O pregão anterior à data de referência ainda vale.
    armazenamento.save_consenso_yahoo(
        [
            {
                "ticker": "PETR4",
                "recomendacao_media": 2.1,
                "analistas": 12,
                "alvo_medio": 15.4,
            }
        ],
        calendario.pregao_anterior(ref).isoformat(),
        agora.isoformat(),
    )
    assert FRASE in cliente.get("/consultor", headers=AUTH).text


def _serie(n: int, inicio: float, passo: float) -> dict:
    t0 = 1_700_000_000
    return {
        "timestamp": [t0 + i * 86400 for i in range(n)],
        "indicators": {
            "quote": [
                {
                    "close": [inicio + i * passo for i in range(n)],
                    "volume": [1_000_000 + (i % 7) * 1000 for i in range(n)],
                }
            ]
        },
    }


def test_decisao_igual_com_e_sem_a_tabela(monkeypatch):
    from app.consultor import calculador

    historicos = {"^BVSP": _serie(260, 100_000, 50)}
    for i, t in enumerate(CARTEIRA_IBOVESPA[:6]):
        historicos[t] = _serie(260, 20 + i, (-1) ** i * 0.05 * (i + 1))
    monkeypatch.setattr(
        calculador, "get_historico_diario", lambda *a, **k: dict(historicos)
    )

    def decisoes() -> dict[str, str]:
        dados = calculador.calcular_consultor(ignorar_cache=True)
        consenso_yahoo.anexar(dados["resultados"], _data_pagina(_agora()))
        return {
            item["ticker"]: grupo
            for grupo, itens in dados["resultados"].items()
            for item in itens
        }

    sem = decisoes()
    data = calendario.ultimo_pregao_fechado(_agora()).isoformat()
    armazenamento.save_consenso_yahoo(
        [
            {
                "ticker": t,
                "recomendacao_media": 1.2,
                "analistas": 20,
                "alvo_medio": 99.0,
            }
            for t in CARTEIRA_IBOVESPA
        ],
        data,
        _agora().isoformat(),
    )
    com = decisoes()
    assert sem == com
    assert any(g != "Sem sinal" for g in com.values())


def test_bloqueio_de_7_dias_vira_candidato_a_poda():
    agora = _agora()
    desde = agora - timedelta(days=8)
    info = {
        "ultima": None,
        "status": {
            "status": "pausa",
            "motivo": "HTTP 401",
            "desde": desde.isoformat(),
            "ultima_tentativa": (agora - timedelta(hours=2)).isoformat(),
        },
    }
    item = sistema_servico.verificar_consenso_yahoo(info, agora)
    assert item.nivel == sistema_servico.ATENCAO
    assert "candidato à poda: remover o coletor numa spec de poda" in item.resumo
    assert item.envelhece is False

    info["status"]["desde"] = (agora - timedelta(days=2)).isoformat()
    assert (
        "candidato à poda"
        not in sistema_servico.verificar_consenso_yahoo(info, agora).resumo
    )


def test_bloqueio_que_continua_mantem_o_inicio():
    inicio = _agora() - timedelta(days=3)
    with respx.mock(assert_all_called=False) as mock:
        crumb, _ = _rotas_yahoo(mock, {})
        crumb.mock(return_value=httpx.Response(401))
        coletor.collect_and_save(inicio)
        coletor.collect_and_save(inicio + timedelta(days=2))
        assert crumb.call_count == 2
    st = armazenamento.get_consenso_yahoo_status()
    assert st["desde"] == inicio.isoformat()
