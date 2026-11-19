"""Aceite da spec 185: o radar sem alerta diz há quantos pregões acendeu.

Sem rede: a função pura recebe o histórico do exemplo; a tela lê o snapshot
`instrumentacao` gravado no banco temporário do teste, com os getters dos
radares trocados por payloads vazios e frescos e o relógio congelado.
"""

from __future__ import annotations

import os
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

import app.banco
from app.services import radares
from app.services.radares import RADARES
from devagent.aceite import exigir_spec_done
from tests.test_aceite_150 import GETTERS, _snap, client

RAIZ = Path(__file__).resolve().parent.parent
BRT = timezone(timedelta(hours=-3))
# 19/11/2026, 11:00 BRT, pregão aberto (exemplo da spec).
AGORA = datetime(2026, 11, 19, 14, 0, tzinfo=timezone.utc)
FRESCO = datetime(2026, 11, 19, 10, 55, tzinfo=BRT)

HISTORICO = {
    date(2026, 11, 19): {
        "radares_pregao": 8,
        "escondidos_pregao": {
            "variacao_subita": 8,
            "exaustao_alta": 8,
            "faca_caindo": 5,
        },
    },
    date(2026, 11, 18): {
        "radares_pregao": 40,
        "escondidos_pregao": {
            "variacao_subita": 37,
            "exaustao_alta": 40,
            "faca_caindo": 40,
        },
    },
    date(2026, 11, 17): {
        "radares_pregao": 30,
        "escondidos_pregao": {
            "variacao_subita": 30,
            "exaustao_alta": 30,
            "faca_caindo": 30,
        },
    },
}

FRASES = {
    "Variação Súbita": "· último alerta há 1 pregão (18/11)",
    "Exaustão de Alta": "· sem alerta nos 3 pregões registrados",
    "Radar de Faca Caindo": "· teve alerta mais cedo neste pregão",
}


@pytest.fixture(autouse=True)
def _spec_done():
    exigir_spec_done("185")


# --- cálculo ---------------------------------------------------------------


def test_janela_comeca_no_pregao_corrente():
    pregoes = radares.janela_pregoes(AGORA)
    assert len(pregoes) == 20
    assert pregoes[:5] == [
        date(2026, 11, 19),
        date(2026, 11, 18),
        date(2026, 11, 17),
        date(2026, 11, 16),
        date(2026, 11, 13),
    ]
    assert pregoes == sorted(pregoes, reverse=True)


def test_exemplo_de_ponta_a_ponta():
    r = radares.ultimo_alerta(HISTORICO, radares.janela_pregoes(AGORA))
    assert r["janela"] == 20
    assert r["registrados"] == 3
    assert r["radares"]["variacao_subita"] == {
        "ultimo": date(2026, 11, 18),
        "pregoes_atras": 1,
    }
    assert r["radares"]["faca_caindo"]["pregoes_atras"] == 0
    assert r["radares"]["faca_caindo"]["ultimo"] == date(2026, 11, 19)
    assert r["radares"]["exaustao_alta"] == {"ultimo": None, "pregoes_atras": None}
    assert set(r["radares"]) == {c for c, _n, _f in RADARES}


def test_sem_o_snapshot_de_18():
    historico = {d: p for d, p in HISTORICO.items() if d != date(2026, 11, 18)}
    r = radares.ultimo_alerta(historico, radares.janela_pregoes(AGORA))
    assert r["registrados"] == 2
    assert r["radares"]["variacao_subita"]["ultimo"] is None
    assert radares.frase_ultimo_alerta("variacao_subita", r) == (
        "· sem alerta nos 2 pregões registrados"
    )


def test_antes_da_primeira_rodada_conta_pregoes_do_calendario():
    historico = {d: p for d, p in HISTORICO.items() if d != date(2026, 11, 19)}
    oito_horas = datetime(2026, 11, 19, 11, 0, tzinfo=timezone.utc)
    r = radares.ultimo_alerta(historico, radares.janela_pregoes(oito_horas))
    assert r["radares"]["variacao_subita"]["pregoes_atras"] == 1
    assert radares.frase_ultimo_alerta("variacao_subita", r) == (
        "· último alerta há 1 pregão (18/11)"
    )


@pytest.mark.parametrize("rodadas", [None, True, 0, "40", 2.5])
def test_dia_sem_rodadas_inteiras_nao_e_registro(rodadas):
    payload = {"escondidos_pregao": {}}
    if rodadas is not None:
        payload["radares_pregao"] = rodadas
    pregoes = [date(2026, 11, 19)]
    r = radares.ultimo_alerta({pregoes[0]: payload}, pregoes)
    assert r["registrados"] == 0
    assert all(i["ultimo"] is None for i in r["radares"].values())
    assert radares.frase_ultimo_alerta("variacao_subita", r) == ""


def test_chave_ausente_num_dia_com_registro_conta_como_acesa():
    pregoes = [date(2026, 11, 19), date(2026, 11, 18)]
    r = radares.ultimo_alerta(
        {pregoes[1]: {"radares_pregao": 10, "escondidos_pregao": {}}}, pregoes
    )
    assert r["registrados"] == 1
    for info in r["radares"].values():
        assert info == {"ultimo": pregoes[1], "pregoes_atras": 1}


def test_plural_e_singular():
    pregoes = radares.janela_pregoes(AGORA)
    so_um = {pregoes[0]: {"radares_pregao": 3, "escondidos_pregao": {"faca_caindo": 3}}}
    r = radares.ultimo_alerta(so_um, pregoes)
    assert radares.frase_ultimo_alerta("faca_caindo", r) == (
        "· sem alerta no 1 pregão registrado"
    )
    tres_atras = {pregoes[3]: {"radares_pregao": 3, "escondidos_pregao": {}}}
    r = radares.ultimo_alerta(tres_atras, pregoes)
    assert radares.frase_ultimo_alerta("faca_caindo", r) == (
        "· último alerta há 3 pregões (16/11)"
    )


# --- tela e snapshot ---------------------------------------------------------


@pytest.fixture
def pagina(monkeypatch):
    class Relogio(datetime):
        @classmethod
        def now(cls, tz=None):  # type: ignore[override]
            return AGORA if tz is None else AGORA.astimezone(tz)

    monkeypatch.setattr("app.main.datetime", Relogio)
    estado = {chave: _snap(chave, FRESCO) for chave in GETTERS}
    for chave, (modulo, funcao) in GETTERS.items():
        monkeypatch.setattr(f"{modulo}.{funcao}", lambda *a, _c=chave, **k: estado[_c])
    return estado


def _gravar_exemplo():
    for dia, payload in HISTORICO.items():
        app.banco.gravar_snapshot("instrumentacao", dia, "ao_vivo", "sistema", payload)


def _secao(html: str) -> str:
    m = re.search(r'<section class="[^"]*aviso-vazio[^"]*".*?</section>', html, re.S)
    assert m, "seção Sem alertas ausente"
    return m.group(0)


def _itens(html: str) -> dict[str, str]:
    """Nome -> frase do `span.ultimo-alerta` ("" sem span), da lista Sem alertas."""
    m = re.search(r'<ul class="radares-sem-alerta">(.*?)</ul>', _secao(html), re.S)
    assert m
    saida = {}
    for li in re.findall(r"<li>(.*?)</li>", m.group(1), re.S):
        span = re.search(r'<span class="ultimo-alerta">(.*?)</span>', li, re.S)
        nome = re.sub(r"<span.*", "", li, flags=re.S).strip()
        saida[nome] = span.group(1).strip() if span else ""
    return saida


def test_tela_mostra_as_frases_do_exemplo(pagina):
    _gravar_exemplo()
    resp = client.get("/")
    assert resp.status_code == 200
    itens = _itens(resp.text)
    assert list(itens) == [n for _c, n, _f in RADARES]
    for nome, frase in FRASES.items():
        assert itens[nome] == frase
    # Os radares sem nenhuma chave em escondidos_pregao acenderam no pregão corrente.
    assert itens["Radar de volume"] == "· teve alerta mais cedo neste pregão"


def test_sem_instrumentacao_nomes_sem_frase(pagina):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "ultimo-alerta" not in _secao(resp.text)
    assert list(_itens(resp.text)) == [n for _c, n, _f in RADARES]


def test_leitura_que_falha_nao_derruba_a_pagina(pagina, monkeypatch):
    _gravar_exemplo()

    original = app.banco.ler_snapshots_datas

    def falha(painel, datas):
        if painel == "instrumentacao":
            raise RuntimeError("banco fora")
        return original(painel, datas)

    monkeypatch.setattr("app.banco.ler_snapshots_datas", falha)
    resp = client.get("/")
    assert resp.status_code == 200
    assert "ultimo-alerta" not in _secao(resp.text)
    assert list(_itens(resp.text)) == [n for _c, n, _f in RADARES]
    snap = client.get("/api/snapshot").json()["paineis"]["radares_ultimo_alerta"]
    assert snap["registrados"] == 0
    assert all(
        i == {"ultimo": None, "pregoes_atras": None} for i in snap["radares"].values()
    )


def test_data_historica_sem_frase(pagina, monkeypatch):
    _gravar_exemplo()
    import app.main as main

    original = main._get_seletor_context

    def ctx(*args, **kwargs):
        return {
            **original(*args, **kwargs),
            "is_historical": True,
            "data_invalida": False,
        }

    monkeypatch.setattr("app.main._get_seletor_context", ctx)
    resp = client.get("/?data=2026-11-18")
    assert resp.status_code == 200
    assert "ultimo-alerta" not in resp.text
    snap = client.get("/api/snapshot?data=2026-11-18").json()
    assert snap["paineis"]["radares_ultimo_alerta"]["registrados"] == 0


def test_api_snapshot_traz_o_exemplo(pagina):
    _gravar_exemplo()
    snap = client.get("/api/snapshot").json()["paineis"]["radares_ultimo_alerta"]
    assert snap["janela"] == 20
    assert snap["registrados"] == 3
    assert snap["fonte"] == "instrumentacao"
    assert snap["coletado_em"]
    assert set(snap["radares"]) == {c for c, _n, _f in RADARES}
    assert snap["radares"]["variacao_subita"] == {
        "ultimo": "2026-11-18",
        "pregoes_atras": 1,
    }
    assert snap["radares"]["faca_caindo"] == {
        "ultimo": "2026-11-19",
        "pregoes_atras": 0,
    }
    assert snap["radares"]["exaustao_alta"] == {"ultimo": None, "pregoes_atras": None}
    for info in snap["radares"].values():
        assert (info["ultimo"] is None) == (info["pregoes_atras"] is None)
        if info["pregoes_atras"] is not None:
            assert 0 <= info["pregoes_atras"] < snap["janela"]
    # A frase visível usa o mesmo M do snapshot.
    html = client.get("/").text
    assert f"sem alerta nos {snap['registrados']} pregões registrados" in html


def test_390px_sem_rolagem_horizontal(pagina):
    from playwright.sync_api import sync_playwright

    _gravar_exemplo()
    html = client.get("/").text
    css = (RAIZ / "app" / "static" / "tema.css").read_text(encoding="utf-8")
    html = re.sub(r"<script\b[^>]*\bsrc=[^>]*>\s*</script>", "", html)
    html = re.sub(r'<link rel="stylesheet"[^>]*>', f"<style>{css}</style>", html)
    html = re.sub(r'<meta http-equiv="refresh"[^>]*>', "", html)
    with sync_playwright() as p:
        navegador = p.chromium.launch(
            executable_path=os.environ.get("CHROMIUM_PATH") or None
        )
        try:
            aba = navegador.new_page(viewport={"width": 390, "height": 844})
            aba.route("**/*", lambda rota: rota.abort())
            aba.set_content(html)
            medida = aba.evaluate(
                """() => {
                  const ul = document.querySelector('ul.radares-sem-alerta');
                  const r = ul.getBoundingClientRect();
                  return {
                    scroll: document.documentElement.scrollWidth,
                    largura: window.innerWidth,
                    direita: r.right,
                    spans: ul.querySelectorAll('span.ultimo-alerta').length,
                  };
                }"""
            )
        finally:
            navegador.close()
    assert medida["spans"] > 0, medida
    assert medida["scroll"] <= medida["largura"], medida
    assert medida["direita"] <= medida["largura"], medida
