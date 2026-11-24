"""Aceite da spec 183: o que o Ibovespa fez nos 5 pregões depois de cada faixa da Maré.

Sem rede: cálculo com leituras sintéticas, coletor com o Yahoo falso de
`tests/yahoo_falso.py` e tela com um `mare_historico` gravado no banco
temporário do teste.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta, timezone

import httpx
import pytest
from fastapi.testclient import TestClient

import app.banco
from app.collectors import mare_historico
from app.collectors.mare import buscar_ibov
from app.database import MareData, save_mare_data
from app.services import mare
from devagent.aceite import exigir_spec_done
from tests import yahoo_falso


@pytest.fixture(autouse=True)
def _spec_done():
    exigir_spec_done("183")


def _leituras(valores, ibovs, inicio=date(2026, 1, 5)):
    saida = []
    d = inicio
    for v, i in zip(valores, ibovs):
        while d.weekday() >= 5:
            d += timedelta(days=1)
        saida.append(
            {
                "data": d.isoformat(),
                "valor": v,
                "fluxo": 50.0,
                "calma": 50.0,
                "volume": 50.0,
                "ibov": i,
            }
        )
        d += timedelta(days=1)
    return saida


def _faixa(mem, nome):
    return next(f for f in mem["faixas"] if f["faixa"] == nome)


# --- cálculo ---------------------------------------------------------------


def test_exemplo_de_ponta_a_ponta():
    leituras = _leituras(
        [15, 15, 50, 50, 50, 50, 50],
        [100_000, 101_000, 99_000, 100_000, 102_000, 103_000, 104_050],
    )
    mem = mare.memoria(leituras, "Neutro")
    assert mem["horizonte"] == 5
    panico = _faixa(mem, "Pânico")
    assert panico["casos"] == 2
    assert panico["media"] is None
    assert panico["positivos"] is None
    assert panico["confianca"] == "poucos casos"
    assert mem["todos"] == {"casos": 2, "media": 3.01, "positivos": 100}
    assert mem["de"] == leituras[0]["data"]
    assert mem["ate"] == leituras[1]["data"]
    assert mem["faixa_hoje"] == "Neutro"


def test_exemplo_com_10_casos():
    retornos = [3, 2, 2, 1, 1, 1, 0, -1, -1, -2]
    # Dez casos em Medo (valor 30) e cinco leituras de fecho, com a série
    # encadeada: ibov[i+5] = ibov[i] * (1 + r/100).
    ibovs = [100.0] * 15
    for i, r in enumerate(retornos):
        ibovs[i + 5] = ibovs[i] * (1 + r / 100)
    valores = [30] * 10 + [50] * 5
    mem = mare.memoria(_leituras(valores, ibovs), "Medo")
    medo = _faixa(mem, "Medo")
    assert medo["casos"] == 10
    assert medo["media"] == 0.60
    assert medo["positivos"] == 60
    assert medo["confianca"] == "baixa"


def test_trinta_casos_e_confianca_moderada():
    n = 35
    mem = mare.memoria(_leituras([70] * n, [100.0 + i for i in range(n)]), None)
    confianca = _faixa(mem, "Confiança")
    assert confianca["casos"] == 30
    assert confianca["confianca"] == "moderada"
    assert confianca["positivos"] == 100
    # Sem faixa de hoje, vale a da última leitura do histórico.
    assert mem["faixa_hoje"] == "Confiança"


def test_leitura_sem_ibov_fica_de_fora_e_faixas_sempre_cinco():
    leituras = _leituras([50] * 12, [100.0 + i for i in range(12)])
    leituras[3]["ibov"] = None
    mem = mare.memoria(leituras, "Neutro")
    # 11 leituras com ibov, 6 casos.
    assert mem["todos"]["casos"] == 6
    assert [f["faixa"] for f in mem["faixas"]] == mare.FAIXAS
    assert sum(f["casos"] for f in mem["faixas"]) == mem["todos"]["casos"]
    assert _faixa(mem, "Otimismo extremo")["casos"] == 0


def test_sem_ibov_nenhum_e_null():
    leituras = _leituras([50] * 20, [None] * 20)
    assert mare.memoria(leituras, "Neutro") is None
    assert mare.memoria([], "Neutro") is None


# --- coletor -----------------------------------------------------------------


def test_coletor_grava_o_fechamento_do_ibovespa(monkeypatch):
    yahoo_falso.instalar(monkeypatch)

    assert mare_historico.collect_and_save() is True
    payload = app.banco.ler_snapshot("mare_historico")
    with httpx.Client() as client:
        ibov = buscar_ibov(client)
    assert payload["leituras"]
    for x in payload["leituras"]:
        assert x["ibov"] == ibov.get(date.fromisoformat(x["data"]))
    assert any(x["ibov"] is not None for x in payload["leituras"])


# --- snapshot e tela ---------------------------------------------------------


@pytest.fixture
def calendario_fixo(monkeypatch):
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


def _gravar_mare(valor: int) -> None:
    save_mare_data(
        MareData(
            timestamp=datetime(2026, 10, 6, 17, 30, tzinfo=timezone.utc),
            valor=valor,
            fluxo=50.0,
            calma=50.0,
            volume=50.0,
            ativos_json="[]",
            historico_json="[]",
            fonte="yfinance",
        )
    )


def _gravar_historico(leituras) -> None:
    app.banco.gravar_snapshot(
        "mare_historico",
        date.fromisoformat(leituras[-1]["data"]),
        "final",
        "yfinance",
        {
            "leituras": leituras,
            "heatmap_ondas": [],
            "heatmap_mare": [],
            "ate": leituras[-1]["data"],
            "fonte": "yfinance",
            "coletado_em": "2026-10-06T21:30:00+00:00",
        },
    )


def _historico_sintetico():
    """15 casos em Medo (+0,60% de média, 60% positivos) e 3 em Pânico."""
    retornos = [3, 2, 2, 1, 1, 1, 0, -1, -1, -2, 2, 1, 1, 0, -1]
    valores = [30] * 15 + [10] * 3 + [50] * 5
    ibovs = [100.0] * len(valores)
    for i, r in enumerate(retornos):
        ibovs[i + 5] = ibovs[i] * (1 + r / 100)
    # Os 3 casos em Pânico apontam para leituras já fixadas acima (i+5 ≥ 20).
    return _leituras(valores, ibovs)


def _cliente():
    from app.main import app as aplicacao

    return TestClient(aplicacao)


def test_snapshot_antigo_sem_ibov(calendario_fixo):
    leituras = _leituras([30] * 30, [None] * 30)
    for x in leituras:
        del x["ibov"]
    _gravar_historico(leituras)
    _gravar_mare(30)
    cliente = _cliente()
    mare_snap = cliente.get("/api/snapshot").json()["paineis"]["mare"]
    assert mare_snap["memoria"] is None
    assert mare_snap["niveis"] == mare.niveis(app.banco.ler_snapshot("mare_historico"))
    assert mare_snap["niveis"]["ondas"] is not None
    html = cliente.get("/").text  # spec 195: o bloco foi para o painel geral
    assert "Depois de cada faixa" in html
    assert "Memória em formação" in html
    assert "mare-memoria-tabela" not in html


def test_snapshot_e_tela_com_historico(calendario_fixo):
    leituras = _historico_sintetico()
    _gravar_historico(leituras)
    _gravar_mare(30)  # Medo hoje
    cliente = _cliente()

    mem = cliente.get("/api/snapshot").json()["paineis"]["mare"]["memoria"]
    assert mem["horizonte"] == 5
    assert mem["faixa_hoje"] == "Medo"
    assert [f["faixa"] for f in mem["faixas"]] == mare.FAIXAS
    assert sum(f["casos"] for f in mem["faixas"]) == mem["todos"]["casos"]
    medo = _faixa(mem, "Medo")
    assert medo["casos"] == 15
    assert medo["confianca"] == "baixa"
    assert (medo["media"], medo["positivos"]) == (0.60, 60)
    assert mem["ate"] < leituras[-1]["data"]

    html = cliente.get("/?nivel=ondas").text  # spec 195
    assert "Depois de cada faixa" in html
    de = date.fromisoformat(mem["de"]).strftime("%d/%m/%Y")
    ate = date.fromisoformat(mem["ate"]).strftime("%d/%m/%Y")
    media = f"{medo['media']:+.2f}%".replace(".", ",")
    assert (
        f"Nos {medo['casos']} pregões entre {de} e {ate} em que a Maré fechou em "
        f"Medo, o Ibovespa andou em média {media} nos 5 pregões seguintes e "
        f"subiu em {medo['positivos']}% deles."
    ) in html
    assert "andou em média +0,60%" in html
    assert re.search(
        r'class="mare-memoria-hoje">\s*<th scope="row">Medo <span class="selo">hoje</span>',
        html,
    )
    assert html.count('<span class="selo">hoje</span>') == 1
    assert re.search(
        r'<th scope="row">Pânico</th>\s*<td class="n num">3</td>\s*<td[^>]*>poucos casos</td>',
        html,
    )
    # Método: fonte, data, ressalvas e confiança.
    assert "Fonte yfinance, coleta de 06/10/2026 18:30 BRT" in html
    for ressalva in (
        "janelas de 5 se sobrepõem",
        "cesta de ações de hoje",
        "não uma previsão",
    ):
        assert ressalva in html
    assert "Na faixa de hoje (Medo): baixa" in html


def test_bloco_na_tela_em_qualquer_nivel(calendario_fixo):
    _gravar_historico(_historico_sintetico())
    _gravar_mare(30)
    cliente = _cliente()
    for nivel in ("marolas", "ondas", "mare"):
        assert "Depois de cada faixa" in cliente.get(f"/?nivel={nivel}").text


def test_fragmento_e_pagina_inicial_sem_o_bloco(calendario_fixo):
    _gravar_historico(_historico_sintetico())
    _gravar_mare(30)
    cliente = _cliente()
    assert "Depois de cada faixa" not in cliente.get("/mare/card?nivel=ondas").text
    # Spec 195: a tela solo /mare volta a ter só o card.
    assert "Depois de cada faixa" not in cliente.get("/mare").text


def test_media_formatada_no_padrao_brasileiro():
    mem = mare.memoria(_historico_sintetico(), "Medo")
    view = mare.view_memoria(mem, {"fonte": "yfinance"})
    medo = next(x for x in view["linhas"] if x["faixa"] == "Medo")
    assert (
        medo["media"]
        == "+" + f"{_faixa(mem, 'Medo')['media']:.2f}".replace(".", ",") + "%"
    )
    assert json.dumps(mem)  # serializável no /api/snapshot


@pytest.mark.parametrize("largura", [360, 390, 1440])
def test_tabela_nao_rola_para_o_lado(calendario_fixo, largura):
    import os
    from pathlib import Path

    from playwright.sync_api import sync_playwright

    _gravar_historico(_historico_sintetico())
    _gravar_mare(30)
    html = _cliente().get("/").text  # spec 195
    css = (Path(__file__).resolve().parents[1] / "app/static/tema.css").read_text(
        encoding="utf-8"
    )
    pagina = re.sub(r"<script\b[^>]*\bsrc=[^>]*>\s*</script>", "", html)
    pagina = re.sub(r'<link rel="stylesheet"[^>]*>', f"<style>{css}</style>", pagina)
    pagina = pagina.replace('<meta http-equiv="refresh" content="900">', "")
    with sync_playwright() as p:
        navegador = p.chromium.launch(
            executable_path=os.environ.get("CHROMIUM_PATH") or None
        )
        try:
            aba = navegador.new_page(viewport={"width": largura, "height": 900})
            aba.route("**/*", lambda rota: rota.abort())
            aba.set_content(pagina)
            if os.environ.get("CAPTURA_183"):
                aba.screenshot(
                    path=f"{os.environ['CAPTURA_183']}/mare-{largura}.png",
                    full_page=True,
                )
            m = aba.evaluate(
                """() => {
                  const t = document.querySelector('.mare-memoria-tabela').getBoundingClientRect();
                  const p = document.querySelector('.mare-memoria').getBoundingClientRect();
                  return {scroll: document.documentElement.scrollWidth,
                          largura: window.innerWidth, tabela: t.right, painel: p.right};
                }"""
            )
        finally:
            navegador.close()
    assert m["scroll"] <= m["largura"], m
    assert m["tabela"] <= m["painel"] + 1, m
