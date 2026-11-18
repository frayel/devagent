"""Aceite da spec 149: a grade não deixa célula vazia entre os painéis macro.

O empacotador percorre, na ordem do HTML, os filhos diretos de `main.grade`
com classe `span-N` visíveis na visão geral (regra do `app/static/ui.js`:
sem `escondido` e, se forem `.painel`, com `visao-geral` ou sem nenhuma das
classes `sentimento-risco`, `rankings`, `alertas`). Toda linha tem de fechar
sem resto. Sem rede: os dados entram direto no banco do teste.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from html.parser import HTMLParser

import pytest
from fastapi.testclient import TestClient

from app.database import (
    ClimaGlobalData,
    ConcentracaoData,
    ConcentracaoSetorialData,
    MotoresIndiceData,
    save_clima_global_data,
    save_concentracao_data,
    save_concentracao_setorial_data,
    save_concentracao_vendedora_data,
    save_motores_indice_data,
)
from app.main import app
from devagent.aceite import exigir_spec_done

client = TestClient(app)

ABAS = ("sentimento-risco", "rankings", "alertas")
SPAN = re.compile(r"^span-(\d+)$")
VAZIOS = {"br", "img", "input", "hr", "meta", "link", "source", "wbr"}

# Títulos dos painéis da visão geral no template em 14/11/2026, mais nada.
TITULOS_PERMITIDOS = {
    "Ibovespa hoje",
    "Maré do mercado",
    "Clima Global",
    "Motores do Índice",
    "Fator Peso Pesado",
    "Concentração Setorial",
    "Pressão Vendedora",
    "Concentração de Ganhos",
    "Apetite e rotação",  # spec 176
}


def test_aceite_149_spec_done():
    exigir_spec_done("149")


class _Filhos(HTMLParser):
    """Filhos diretos de `main.grade`: (classes, título do primeiro h2)."""

    def __init__(self) -> None:
        super().__init__()
        self.filhos: list[dict] = []
        self._pilha: list[str] = []
        self._nivel_grade: int | None = None
        self._no_h2 = False

    def handle_starttag(self, tag, attrs):
        if tag in VAZIOS:
            return
        classes = (dict(attrs).get("class") or "").split()
        if self._nivel_grade is None and tag == "main" and "grade" in classes:
            self._pilha.append(tag)
            self._nivel_grade = len(self._pilha)
            return
        self._pilha.append(tag)
        if self._nivel_grade is not None and len(self._pilha) == self._nivel_grade + 1:
            self.filhos.append({"classes": classes, "titulo": None})
        if tag == "h2" and self.filhos and self.filhos[-1]["titulo"] is None:
            self._no_h2 = True

    def handle_endtag(self, tag):
        if tag in VAZIOS or not self._pilha:
            return
        if tag == "h2":
            self._no_h2 = False
        # Fecha até a tag correspondente (HTML tolerante).
        while self._pilha:
            topo = self._pilha.pop()
            if self._nivel_grade is not None and len(self._pilha) < self._nivel_grade:
                self._nivel_grade = -1  # saiu da grade
            if topo == tag:
                break

    def handle_data(self, data):
        if self._no_h2 and data.strip():
            self.filhos[-1]["titulo"] = data.strip()
            self._no_h2 = False


def _visivel_na_visao_geral(classes: list[str]) -> bool:
    if "escondido" in classes:
        return False
    if "painel" in classes:
        return "visao-geral" in classes or not any(a in classes for a in ABAS)
    return True


def _span(classes: list[str]) -> int | None:
    for c in classes:
        m = SPAN.match(c)
        if m:
            return int(m.group(1))
    return None


def _visiveis(html: str) -> list[tuple[str, int]]:
    p = _Filhos()
    p.feed(html)
    saida = []
    for f in p.filhos:
        span = _span(f["classes"])
        if span is None or not _visivel_na_visao_geral(f["classes"]):
            continue
        nome = f["titulo"] if "painel" in f["classes"] else None
        saida.append((nome or " ".join(f["classes"]), span))
    return saida


def empacotar(spans: list[int], colunas: int) -> list[int]:
    """Restos das linhas que fecharam com sobra (vazio = empacota sem resto)."""
    restos = []
    resta = colunas
    for s in spans:
        s = min(s, colunas)
        if s > resta:
            restos.append(resta)
            resta = colunas
        resta -= s
        if resta == 0:
            resta = colunas
    if resta != colunas:
        restos.append(resta)
    return restos


def em_6_colunas(span: int) -> int:
    # tema.css, 768 a 1199px: span-3 e span-4 valem 3; span-6 ou mais, 6.
    return 3 if span <= 4 else 6


def _semear(com_setorial: bool) -> None:
    agora = datetime.now(timezone.utc)
    save_clima_global_data(
        ClimaGlobalData(timestamp=agora, sp500_pct=0.5, vix_pct=-1.2, status="Risk-on")
    )
    save_motores_indice_data(
        MotoresIndiceData(
            timestamp=agora,
            motores_json=json.dumps([{"nome": "Financeiro", "variacao": 1.2}]),
            fonte="yfinance",
            pregao_data=agora.date().isoformat(),
        )
    )
    conc = ConcentracaoData(
        timestamp=agora,
        resumo_json=json.dumps(
            {"estado": "concentrado", "mensagem": "Dos 1000 pontos..."}
        ),
        top3_json=json.dumps([{"ticker": "VALE3", "pontos": 500, "peso": 0.12}]),
    )
    save_concentracao_data(conc)
    save_concentracao_vendedora_data(conc)
    if com_setorial:
        save_concentracao_setorial_data(
            ConcentracaoSetorialData(
                timestamp=agora, setor_destaque="Financeiro", variacao_media=1.1
            )
        )


def _home(com_setorial: bool) -> list[tuple[str, int]]:
    _semear(com_setorial)
    resp = client.get("/")
    assert resp.status_code == 200
    return _visiveis(resp.text)


def _paineis(visiveis):
    return [t for t, _ in visiveis if t in TITULOS_PERMITIDOS]


@pytest.mark.parametrize("com_setorial", [True, False])
def test_12_colunas_fecham(com_setorial):
    visiveis = _home(com_setorial)
    titulos = _paineis(visiveis)
    for esperado in (
        "Clima Global",
        "Motores do Índice",
        "Fator Peso Pesado",
        "Pressão Vendedora",
        "Concentração de Ganhos",
    ):
        assert esperado in titulos, (esperado, visiveis)
    assert ("Concentração Setorial" in titulos) is com_setorial
    assert empacotar(_com_mare_em_duas_linhas(visiveis), 12) == [], visiveis


def _com_mare_em_duas_linhas(visiveis) -> list[int]:
    """Spec 176: a Maré tem `grid-row: span 2` na grade de 12 colunas. As colunas
    dela na linha seguinte entram como um span a mais, logo depois dela."""
    spans = []
    for titulo, s in visiveis:
        spans.append(s)
        if titulo == "Maré do mercado":
            spans.append(s)
    return spans


@pytest.mark.parametrize("com_setorial", [True, False])
def test_6_colunas_do_fator_em_diante(com_setorial):
    visiveis = _home(com_setorial)
    inicio = [t for t, _ in visiveis].index("Fator Peso Pesado")
    spans = [em_6_colunas(s) for _, s in visiveis[inicio:]]
    assert empacotar(spans, 6) == [], visiveis[inicio:]


@pytest.mark.parametrize("com_setorial", [True, False])
def test_so_titulos_existentes_na_visao_geral(com_setorial):
    for titulo, _ in _home(com_setorial):
        if titulo.startswith("span-"):
            continue  # filho da grade que não é painel (manchete, abas)
        assert titulo in TITULOS_PERMITIDOS, titulo


def test_empacotador_ignora_abas_e_acusa_a_main_de_14_11():
    html = """
    <main class="grade">
      <div class="span-12 manchete-container"></div>
      <section class="painel span-8 visao-geral"><h2>Ibovespa hoje</h2></section>
      <section class="painel span-4 visao-geral"><h2>Maré do mercado</h2></section>
      <section class="painel span-6 visao-geral"><h2>Clima Global</h2></section>
      <section class="painel span-6 visao-geral"><h2>Motores do Índice</h2></section>
      <section class="painel span-4 visao-macro sentimento-risco"><h2>Dispersão</h2></section>
      <section class="painel span-4 visao-macro sentimento-risco"><h2>Índice de Coesão</h2></section>
      <section class="painel span-4 visao-geral"><h2>Fator Peso Pesado</h2></section>
      <section class="painel span-4 visao-geral"><h2>Concentração Setorial</h2></section>
      <section class="painel span-12 visao-geral"><h2>Pressão Vendedora</h2></section>
      <section class="painel span-12 visao-geral"><h2>Concentração de Ganhos</h2></section>
    </main>
    """
    visiveis = _visiveis(html)
    titulos = [t for t, _ in visiveis]
    assert "Dispersão" not in titulos and "Índice de Coesão" not in titulos
    assert empacotar([s for _, s in visiveis], 12) == [4]
    # Fator 4 + Concentração 8 fecha em 12, mas não em 6 colunas.
    assert empacotar([4, 8, 12, 12], 12) == []
    assert empacotar([em_6_colunas(s) for s in (4, 8, 12, 12)], 6) == [3]
