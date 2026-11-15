"""Aceite da spec 146: a página inicial não esconde erro de execução.

Três frentes, todas sem internet:

1. `GET /` com o banco de demonstração completo e com cada um dos quatro cards
   críticos ausente (Ibovespa, Maré, Dispersão, Motores). O ausente mostra o
   estado indisponível, nunca um KPI numérico vazio no lugar dele.
2. A inicialização de `app/static/graficos.js` e `app/static/ui.js` roda sobre
   esse HTML no Chromium headless, com toda a rede abortada e um Plotly falso.
   Qualquer `pageerror` ou `console.error` dos dois arquivos falha o teste.
   O Chromium ausente faz o teste falhar, não pular: o job `test` do CI instala
   o navegador antes do `make verify`.
3. Um coletor que falha grava log sem o segredo do ambiente, e a home responde.

Não há aqui nenhuma mensagem de console "dos dois erros" de 05/11/2026: elas
nunca foram capturadas, e o teste não as inventa.
"""

from __future__ import annotations

import logging
import os
import re
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import app.database
from devagent.aceite import exigir_spec_done

RAIZ = Path(__file__).resolve().parents[1]
STATIC = RAIZ / "app" / "static"

INDISPONIVEL = "Dado indisponível agora."

# Card crítico -> (classe que identifica a seção, onde o dado é lido em app.main).
CARDS = {
    "ibovespa": ("painel-ibovespa", "app.main.get_ibovespa_view_data"),
    "mare": ("painel-mare", "app.main.mare_servico.get_mare_view"),
    "dispersao": ("sentimento-risco", "app.main.get_highlights_view_data"),
    "motores": ("painel-motores-indice", "app.main.get_latest_motores_indice_data"),
}


def test_aceite_146_spec_done():
    exigir_spec_done("146")


def _semear() -> None:
    """Banco de demonstração do `scripts/telas.py`, no banco temporário do teste."""
    sys.path.insert(0, str(RAIZ / "scripts"))
    try:
        import telas
    finally:
        sys.path.remove(str(RAIZ / "scripts"))
    telas._semear(app.database.DB_PATH)


def _home() -> str:
    from app.main import app as aplicacao

    resposta = TestClient(aplicacao).get("/")
    assert resposta.status_code == 200
    return resposta.text


def _secao(pagina: str, classe: str) -> str:
    m = re.search(
        r'<section class="painel[^"]*\b%s\b[^"]*">(.*?)</section>' % re.escape(classe),
        pagina,
        re.S,
    )
    assert m, f"seção {classe} não encontrada na home"
    return m.group(1)


@pytest.fixture
def banco_completo():
    _semear()


def test_home_completa_mostra_os_quatro_cards(banco_completo):
    pagina = _home()
    for card, (classe, _) in CARDS.items():
        assert INDISPONIVEL not in _secao(pagina, classe), card
    assert "Não constitui recomendação de investimento" in pagina


@pytest.mark.parametrize("card", list(CARDS))
def test_card_ausente_mostra_indisponivel(banco_completo, monkeypatch, card):
    classe, alvo = CARDS[card]
    monkeypatch.setattr(alvo, lambda *a, **k: None)
    pagina = _home()
    assert "Não constitui recomendação de investimento" in pagina
    secao = _secao(pagina, classe)
    assert INDISPONIVEL in secao
    # Nem KPI com valor vazio, nem variação solta no lugar do dado ausente.
    assert not re.search(r'class="valor num">\s*(pontos)?\s*</div>', secao)
    assert 'class="var ' not in secao
    assert not re.search(r"\d+,\d+%", secao)


# --- 2. Os scripts da aplicação no Chromium, sem rede ---------------------------

PLOTLY_FALSO = """
window.Plotly = {
  newPlot: function () { return Promise.resolve(); },
  react: function () { return Promise.resolve(); },
  purge: function () {},
  Plots: { resize: function () {} },
};
"""


def _sem_scripts_externos(pagina: str) -> str:
    """Tira as tags de htmx, Plotly e dos dois scripts locais (entram depois)."""
    return re.sub(r"<script\b[^>]*\bsrc=[^>]*>\s*</script>", "", pagina)


def _executar_no_navegador(pagina: str) -> list[str]:
    from playwright.sync_api import sync_playwright

    erros: list[str] = []
    with sync_playwright() as p:
        # CHROMIUM_PATH: navegador já instalado na máquina (o Makefile o acha),
        # para o teste não depender de baixar o da versão do Playwright.
        navegador = p.chromium.launch(
            executable_path=os.environ.get("CHROMIUM_PATH") or None
        )
        try:
            aba = navegador.new_page()
            aba.route("**/*", lambda rota: rota.abort())
            aba.on("pageerror", lambda exc: erros.append(f"pageerror: {exc}"))

            def _console(msg) -> None:
                # Recurso que o próprio teste abortou é rede, não a aplicação.
                if msg.type == "error" and not msg.text.startswith(
                    "Failed to load resource"
                ):
                    erros.append(f"console.error: {msg.text}")

            aba.on("console", _console)
            aba.set_content(_sem_scripts_externos(pagina))
            # O Plotly falso entra antes dos dois scripts da aplicação.
            aba.add_script_tag(content=PLOTLY_FALSO)
            for nome in ("graficos.js", "ui.js"):
                aba.add_script_tag(content=(STATIC / nome).read_text(encoding="utf-8"))
            aba.evaluate(
                "document.dispatchEvent(new Event('DOMContentLoaded'));"
                "window.dispatchEvent(new Event('load'));"
            )
            aba.wait_for_timeout(300)
        finally:
            navegador.close()
    return erros


def test_scripts_da_home_sem_erro_no_navegador(banco_completo):
    pagina = _home()
    assert "grafico-ibovespa" in pagina
    assert _executar_no_navegador(pagina) == []


@pytest.mark.parametrize("card", list(CARDS))
def test_scripts_sem_erro_com_card_ausente(banco_completo, monkeypatch, card):
    monkeypatch.setattr(CARDS[card][1], lambda *a, **k: None)
    assert _executar_no_navegador(_home()) == []


# --- 3. Falha de coletor sem segredo no log -------------------------------------

SENHA = "senha-de-teste-146-xyz"


def test_coletor_que_falha_nao_vaza_segredo(monkeypatch, caplog):
    from app import agendador
    from app.consultor import avaliador_historico

    monkeypatch.setenv("MT5_API_KEY", SENHA)
    monkeypatch.setenv("GITHUB_TOKEN", SENHA + "-gh")
    monkeypatch.setattr(avaliador_historico, "rodar_backtest", lambda: None)

    def quebra():
        raise ConnectionError(
            f"GET https://mt5.exemplo/cotacao?key={SENHA} recusou; chave {SENHA}"
        )

    importar = agendador.importlib.import_module

    def _coletor(nome: str, *a, **k):
        if nome == "app.collectors.ibovespa":
            return SimpleNamespace(collect_and_save=quebra)
        if nome.startswith("app.collectors."):
            return SimpleNamespace(collect_and_save=lambda: True)
        return importar(nome, *a, **k)

    monkeypatch.setattr(agendador.importlib, "import_module", _coletor)
    with caplog.at_level(logging.WARNING):
        agendador.coletar_tudo()

    avisos = [r.getMessage() for r in caplog.records if "ibovespa" in r.getMessage()]
    assert avisos, "a falha do coletor não foi registrada"
    assert any("ConnectionError" in a for a in avisos)
    for texto in [*(r.getMessage() for r in caplog.records), str(agendador.estado)]:
        assert SENHA not in texto

    from app.main import app as aplicacao

    cliente = TestClient(aplicacao)
    coleta = cliente.get("/api/coleta")
    assert SENHA not in coleta.text
    assert cliente.get("/").status_code == 200
