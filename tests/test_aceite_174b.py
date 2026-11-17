"""Aceite da spec 174b: o seletor Marolas, Ondas e Maré no card da Maré.

Sem internet. A leitura de hoje (Marolas) é gravada como em
`tests/test_aceite_173.py`; o `mare_historico` da 174a é um snapshot sintético
no banco temporário do teste. O teste de navegador serve as páginas pelo
próprio `TestClient`, interceptando as requisições do Chromium, no padrão de
`tests/test_aceite_146.py` (o Chromium ausente faz o teste falhar, não pular).
"""

from __future__ import annotations

import json
import os
import re
from datetime import date, datetime, timedelta, timezone
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi.testclient import TestClient

import app.banco
from app.database import MareData, save_mare_data
from app.services import mare as mare_servico
from devagent.aceite import exigir_spec_done

HOJE = date(2026, 10, 6)
ONTEM = date(2026, 10, 5)
MAROLAS = 68

# 200 leituras diárias: 179 em 30 e as 21 mais recentes com 20 em 50 e uma em
# 61. Ondas = (20 × 50 + 61) / 21 = 50,5 → 51; Maré = (179 × 30 + 1061) / 200
# = 32,2 → 32.
VALORES = [30] * 179 + [50] * 20 + [61]
ONDAS = 51
MARE = 32
INICIO = HOJE - timedelta(days=len(VALORES))


def test_aceite_174b_spec_done():
    exigir_spec_done("174b")


@pytest.fixture(autouse=True)
def calendario_fixo(monkeypatch):
    class Mercado:
        def mercado_aberto(self, dt):
            return False

        def pregao_corrente(self, dt):
            return HOJE

        def ultimo_pregao_fechado(self, dt):
            return HOJE

    monkeypatch.setattr("app.main.calendario", Mercado())
    monkeypatch.setattr(
        "app.main.obter_pregoes_disponiveis",
        lambda *a, **k: [HOJE.isoformat(), ONTEM.isoformat()],
    )


def _leituras() -> list[dict]:
    return [
        {
            "data": (INICIO + timedelta(days=i)).isoformat(),
            "valor": v,
            "fluxo": float(v),
            "calma": float(v),
            "volume": float(v),
        }
        for i, v in enumerate(VALORES)
    ]


def _heatmap(prefixo: str) -> list[dict]:
    return [
        {
            "ticker": f"{prefixo}{i}3",
            "variacao": 1.5 - i,
            "financeiro": 1e9,
            "peso": 0.5,
        }
        for i in range(2)
    ]


@pytest.fixture
def com_mare():
    historico = [{"data": f"2026-09-{d:02d}", "valor": 40 + d} for d in range(1, 22)]
    save_mare_data(
        MareData(
            timestamp=datetime(2026, 10, 6, 17, 30, tzinfo=timezone.utc),
            valor=MAROLAS,
            fluxo=74.2,
            calma=61.0,
            volume=67.4,
            ativos_json=json.dumps(_heatmap("HOJE")),
            historico_json=json.dumps(historico),
            fonte="yfinance",
        )
    )


@pytest.fixture
def com_historico(com_mare):
    app.banco.gravar_snapshot(
        "mare_historico",
        HOJE,
        "final",
        "yfinance",
        {
            "leituras": _leituras(),
            "heatmap_ondas": _heatmap("ONDA"),
            "heatmap_mare": _heatmap("MARE"),
        },
    )


def _get(caminho: str) -> str:
    from app.main import app as aplicacao

    resposta = TestClient(aplicacao).get(caminho)
    assert resposta.status_code == 200
    return resposta.text


def _card(html: str) -> str:
    m = re.search(
        r'<section class="painel[^"]*\bpainel-mare\b[^"]*">(.*?)</section>', html, re.S
    )
    assert m, "card da Maré não encontrado"
    return m.group(1)


def _gauge(card: str) -> int:
    m = re.search(r'class="v num">(\d+)<', card)
    assert m, "gauge sem número"
    return int(m.group(1))


def _ativo(card: str) -> str:
    ativos = re.findall(r'data-nivel="(\w+)" aria-current="true"', card)
    assert len(ativos) == 1, ativos
    return ativos[0]


def _links(card: str) -> dict[str, str]:
    return dict(
        (n, h.replace("&amp;", "&"))
        for h, n in re.findall(r'<a href="([^"]*)" data-nivel="(\w+)"', card)
    )


# --- rota e seletor ----------------------------------------------------------


def test_mare_sem_parametro_e_marolas_com_o_valor_de_hoje(com_historico):
    card = _card(_get("/mare"))
    assert _ativo(card) == "marolas"
    assert _gauge(card) == MAROLAS
    for rotulo, janela in (
        ("Marolas", "hoje"),
        ("Ondas", "21 pregões"),
        ("Maré", "252 pregões"),
    ):
        assert f'{rotulo} <span class="janela">{janela}</span>' in card


def test_mare_ondas_mostra_o_valor_do_snapshot(com_historico):
    card = _card(_get("/mare?nivel=ondas"))
    assert _ativo(card) == "ondas"
    assert _gauge(card) == ONDAS
    from app.main import app as aplicacao

    snap = TestClient(aplicacao).get("/api/snapshot").json()
    assert snap["paineis"]["mare"]["niveis"]["ondas"]["valor"] == ONDAS
    assert snap["paineis"]["mare"]["niveis"]["mare"]["valor"] == MARE


def test_nivel_desconhecido_vale_marolas(com_historico):
    card = _card(_get("/mare?nivel=xyz"))
    assert _ativo(card) == "marolas"
    assert _gauge(card) == MAROLAS


def test_fragmento_traz_so_o_card_de_mare(com_historico):
    html = _get("/mare/card?nivel=mare")
    assert "<html" not in html
    assert "Não constitui recomendação de investimento" not in html
    card = _card(html)
    assert _ativo(card) == "mare"
    assert _gauge(card) == MARE
    assert "MARE03" in card and "HOJE03" not in card


def test_painel_geral_com_ondas(com_historico):
    card = _card(_get("/?nivel=ondas"))
    assert _ativo(card) == "ondas"
    assert _gauge(card) == ONDAS
    # Os gauges de Apetite e Rotação continuam fora do conteúdo trocado.
    assert 'class="mare-corpo"' in card


def test_padrao_sem_nivel_e_o_card_de_hoje(com_historico):
    card = _card(_get("/"))
    assert _ativo(card) == "marolas"
    assert _gauge(card) == MAROLAS
    assert "HOJE03" in card


# --- links sem JS ------------------------------------------------------------


def test_cada_opcao_e_link_que_preserva_data(com_historico):
    links = _links(_card(_get(f"/?data={HOJE.isoformat()}&aba=rankings")))
    assert set(links) == {"marolas", "ondas", "mare"}
    for nivel, href in links.items():
        query = parse_qs(urlsplit(href).query)
        assert query["nivel"] == [nivel]
        assert query["data"] == [HOJE.isoformat()]
        assert query["aba"] == ["rankings"]


def test_links_sem_data_quando_ausente(com_historico):
    for nivel, href in _links(_card(_get("/mare"))).items():
        assert parse_qs(urlsplit(href).query) == {"nivel": [nivel]}


# --- contexto e legenda ------------------------------------------------------


def _de_ate(n: int) -> str:
    datas = [INICIO + timedelta(days=i) for i in range(len(VALORES))][-n:]
    return f"de {datas[0]:%d/%m} a {datas[-1]:%d/%m}"


def test_ondas_tem_contexto_e_legenda_da_janela(com_historico):
    card = _card(_get("/mare?nivel=ondas"))
    assert f"média de 21 pregões completos, {_de_ate(21)}" in card
    assert "Área: volume financeiro dos últimos 21 pregões" in card
    assert "ONDA03" in card


def test_marolas_sem_contexto_nem_legenda_de_janela(com_historico):
    card = _card(_get("/mare"))
    # O método (botão i) cita as janelas; a linha de contexto e a legenda, não.
    assert 'class="mare-contexto' not in card
    assert not re.search(r"média de \d+ pregões completos, de", card)
    assert "Área: volume financeiro dos últimos" not in card
    assert "Área: volume financeiro do dia" in card


def test_contexto_do_exemplo_da_spec():
    """`pregoes` 21, `de` 2026-10-17, `ate` 2026-11-14 (exemplo da spec)."""
    datas = [date(2026, 10, 17) + timedelta(days=i) for i in range(20)]
    datas.append(date(2026, 11, 14))
    leituras = [
        {
            "data": d.isoformat(),
            "valor": 50,
            "fluxo": 50.0,
            "calma": 50.0,
            "volume": 50.0,
        }
        for d in datas
    ]
    card = mare_servico.view_nivel(None, {"leituras": leituras}, "ondas")
    assert card is not None
    assert card["contexto"] == "média de 21 pregões completos, de 17/10 a 14/11"


# --- em formação -------------------------------------------------------------


def test_sem_historico_ondas_em_formacao_e_marolas_normal(com_mare):
    card = _card(_get("/mare?nivel=ondas"))
    assert "Histórico da maré em formação: 0 de 15 pregões" in card
    assert 'class="v num"' not in card
    assert _ativo(card) == "ondas"
    card = _card(_get("/mare"))
    assert _gauge(card) == MAROLAS


def test_mare_em_formacao_conta_as_leituras_gravadas(com_mare):
    app.banco.gravar_snapshot(
        "mare_historico", HOJE, "final", "yfinance", {"leituras": _leituras()[:30]}
    )
    card = _card(_get("/mare?nivel=mare"))
    assert "Histórico da maré em formação: 30 de 189 pregões" in card
    assert _gauge(_card(_get("/mare?nivel=ondas"))) == 30


# --- data passada ------------------------------------------------------------


def test_data_passada_sem_historico_mostra_sem_registro(com_historico):
    html = _get(f"/?data={ONTEM.isoformat()}&nivel=mare")
    card = _card(html)
    assert "Sem registro neste pregão" in card
    assert _ativo(card) == "mare"
    assert "painel-ibovespa" in html
    assert "Não constitui recomendação de investimento" in html


def test_fragmento_com_data_le_o_pregao_pedido(com_historico):
    card = _card(_get(f"/mare/card?nivel=ondas&data={ONTEM.isoformat()}"))
    assert "Sem registro neste pregão" in card
    card = _card(_get(f"/mare/card?nivel=ondas&data={HOJE.isoformat()}"))
    assert _gauge(card) == ONDAS


# --- navegador -----------------------------------------------------------------

BASE = "http://painel.teste"


def test_clicar_em_ondas_troca_o_gauge_sem_recarregar(com_historico):
    from playwright.sync_api import sync_playwright

    from app.main import app as aplicacao

    cliente = TestClient(aplicacao)
    pedidos: list[str] = []

    def servir(rota) -> None:
        url = urlsplit(rota.request.url)
        if f"{url.scheme}://{url.netloc}" != BASE:
            rota.abort()
            return
        caminho = url.path + (f"?{url.query}" if url.query else "")
        pedidos.append(caminho)
        resposta = cliente.get(caminho)
        rota.fulfill(
            status=resposta.status_code,
            headers={"content-type": resposta.headers.get("content-type", "text/html")},
            body=resposta.content,
        )

    erros: list[str] = []
    with sync_playwright() as p:
        navegador = p.chromium.launch(
            executable_path=os.environ.get("CHROMIUM_PATH") or None
        )
        try:
            aba = navegador.new_page()
            aba.route("**/*", servir)
            aba.on("pageerror", lambda exc: erros.append(str(exc)))
            aba.goto(f"{BASE}/mare")
            assert aba.inner_text(".painel-mare .g-centro .v") == str(MAROLAS)
            aba.evaluate("window.__marca174b = 'antes do clique'")
            aba.click('.mare-nivel a[data-nivel="ondas"]')
            aba.wait_for_function(
                f"document.querySelector('.painel-mare .g-centro .v')"
                f".textContent.trim() === '{ONDAS}'"
            )
            assert aba.evaluate("window.__marca174b") == "antes do clique"
            assert parse_qs(urlsplit(aba.url).query)["nivel"] == ["ondas"]
            assert (
                aba.get_attribute('.mare-nivel a[aria-current="true"]', "data-nivel")
                == "ondas"
            )
            # Os links do fragmento seguem a página, não /mare/card.
            href = aba.get_attribute('.mare-nivel a[data-nivel="mare"]', "href")
            assert href == "?nivel=mare"
        finally:
            navegador.close()
    assert erros == []
    assert "/mare/card?nivel=ondas" in pedidos
