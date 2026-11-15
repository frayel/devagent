"""Aceite da spec 156: o rodapé mostra o que mudou no painel e onde conferir.

Sem internet: o arquivo de novidades e o dia de hoje são trocados por
`monkeypatch` (`app.services.novidades.CAMINHO` e `.hoje`). O teste do
`?aba=` roda `app/static/ui.js` no Chromium headless, como o da spec 146,
com a página servida por uma rota interceptada e toda outra requisição abortada.
"""

from __future__ import annotations

import json
import os
import re
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app as aplicacao
from app.services import novidades
from devagent.aceite import exigir_spec_done

RAIZ = Path(__file__).resolve().parents[1]
STATIC = RAIZ / "app" / "static"
INDEX = RAIZ / "app" / "templates" / "index.html"
SPECS = RAIZ / "docs" / "specs"

client = TestClient(aplicacao)

EXEMPLO = [
    {
        "data": "2026-11-15",
        "tipo": "melhoria",
        "texto": "O sinal de inflexão aparece num só lugar, com a queda acumulada e a alta de hoje lado a lado.",
        "onde": {
            "aba": "alertas",
            "aba_nome": "Alertas Intraday",
            "painel": "Radar de Inflexão",
        },
        "spec": "151",
    },
    {
        "data": "2026-11-14",
        "tipo": "correcao",
        "texto": "A frase do Fator Peso Pesado escreve o tamanho do movimento sem sinal.",
        "pr": "#836",
    },
    {
        "data": "2026-09-01",
        "tipo": "novidade",
        "texto": "Texto antigo que ficou fora da janela de sessenta dias.",
    },
]


def test_aceite_156_spec_done():
    exigir_spec_done("156")


@pytest.fixture
def arquivo(tmp_path, monkeypatch):
    caminho = tmp_path / "novidades.json"
    monkeypatch.setattr(novidades, "CAMINHO", caminho)
    monkeypatch.setattr(novidades, "hoje", lambda: date(2026, 11, 15))
    return caminho


@pytest.fixture
def exemplo(arquivo):
    arquivo.write_text(json.dumps(EXEMPLO), encoding="utf-8")
    return arquivo


# --- Rodapé, página e snapshot com o exemplo da spec ---------------------------


@pytest.mark.parametrize("rota", ["/", "/sistema", "/novidades"])
def test_rodape_mostra_a_data_da_ultima_novidade(exemplo, rota):
    resposta = client.get(rota)
    assert resposta.status_code == 200
    assert re.search(
        r'<a href="/novidades"[^>]*>Novidades · atualizado em 15/11/2026</a>',
        resposta.text,
    )
    assert "Não constitui recomendação de investimento" in resposta.text


def test_pagina_novidades_agrupa_por_dia_com_onde_ver(exemplo):
    pagina = client.get("/novidades").text
    assert "15/11/2026" in pagina and "14/11/2026" in pagina
    assert pagina.index("15/11/2026</h3>") < pagina.index("14/11/2026</h3>")
    assert ">Melhoria<" in pagina and ">Correção<" in pagina
    assert (
        '<a class="novidade-onde" href="/?aba=alertas">'
        "Onde ver: Alertas Intraday › Radar de Inflexão</a>"
    ) in pagina
    # A correção não tem `onde`: uma só linha de onde ver na página.
    assert pagina.count("Onde ver:") == 1
    assert "Texto antigo" not in pagina
    assert "#836" not in pagina and "151" not in pagina


def test_snapshot_publica_as_novidades_da_janela(exemplo):
    snapshot = client.get("/api/snapshot").json()
    assert [n["data"] for n in snapshot["novidades"]] == ["2026-11-15", "2026-11-14"]
    assert "novidades" not in snapshot["paineis"]


def test_onde_de_pagina(arquivo):
    arquivo.write_text(
        json.dumps(
            [
                {
                    "data": "2026-11-15",
                    "tipo": "novidade",
                    "texto": "Uma página nova.",
                    "onde": {"pagina": "/novidades", "pagina_nome": "Novidades"},
                },
                {
                    "data": "2026-11-15",
                    "tipo": "melhoria",
                    "texto": "Um painel melhor.",
                    "onde": {
                        "pagina": "/sistema",
                        "pagina_nome": "Sistema",
                        "painel": "Estado do sistema",
                    },
                },
            ]
        ),
        encoding="utf-8",
    )
    pagina = client.get("/novidades").text
    assert 'href="/novidades">Onde ver: Novidades</a>' in pagina
    assert 'href="/sistema">Onde ver: Sistema › Estado do sistema</a>' in pagina


def test_sem_entradas_na_janela(arquivo):
    arquivo.write_text(json.dumps(EXEMPLO[2:]), encoding="utf-8")
    assert "Nenhuma novidade nos últimos 60 dias." in client.get("/novidades").text
    # O rodapé usa a maior data mesmo fora da janela.
    assert "Novidades · atualizado em 01/09/2026" in client.get("/").text
    assert client.get("/api/snapshot").json()["novidades"] == []


def test_arquivo_vazio_esconde_o_rodape(arquivo):
    arquivo.write_text("[]", encoding="utf-8")
    assert "Novidades · atualizado" not in client.get("/").text


# --- Plano B: arquivo ausente ou inválido --------------------------------------


@pytest.mark.parametrize("conteudo", [None, "{ não é json", '{"data": "2026-11-15"}'])
def test_arquivo_ausente_ou_invalido_nao_derruba(arquivo, conteudo):
    if conteudo is not None:
        arquivo.write_text(conteudo, encoding="utf-8")
    home = client.get("/")
    assert home.status_code == 200
    assert "Novidades · atualizado" not in home.text
    pagina = client.get("/novidades")
    assert pagina.status_code == 200
    assert "Novidades indisponíveis." in pagina.text
    assert client.get("/api/snapshot").json()["novidades"] == []


# --- O arquivo real -------------------------------------------------------------


def _abas_da_home() -> dict[str, str]:
    html = INDEX.read_text(encoding="utf-8")
    return {
        aba: rotulo.strip()
        for aba, rotulo in re.findall(
            r'<button class="aba-btn[^"]*" data-aba="([^"]+)">([^<]+)</button>', html
        )
    }


def _reais() -> list[dict]:
    dados = json.loads((RAIZ / "app" / "novidades.json").read_text(encoding="utf-8"))
    assert isinstance(dados, list) and dados
    return dados


def test_arquivo_real_e_valido():
    abas = _abas_da_home()
    assert {"visao-geral", "alertas"} <= set(abas)
    for entrada in _reais():
        assert entrada["tipo"] in {"novidade", "melhoria", "correcao"}, entrada
        date.fromisoformat(entrada["data"])
        texto = entrada["texto"]
        assert len(texto) <= 200, texto
        assert ".py" not in texto and "app/" not in texto, texto
        assert not re.search(r"\bspecs?\b", texto, re.I), texto
        assert entrada.get("spec") or entrada.get("pr"), entrada
        onde = entrada.get("onde")
        if onde and "aba" in onde:
            assert onde["aba"] in abas, onde
            assert onde["aba_nome"] == abas[onde["aba"]], onde
        if onde and "pagina" in onde:
            assert client.get(onde["pagina"]).status_code == 200, onde


def test_arquivo_real_do_mais_novo_para_o_mais_antigo():
    datas = [e["data"] for e in _reais()]
    assert datas == sorted(datas, reverse=True)


def _cabecalho(spec: Path) -> dict[str, str]:
    texto = spec.read_text(encoding="utf-8")
    bloco = texto.split("---")[1] if texto.startswith("---") else ""
    campos = {}
    for linha in bloco.splitlines():
        if ":" in linha:
            chave, valor = linha.split(":", 1)
            campos[chave.strip()] = valor.strip()
    return campos


def test_toda_entrega_visivel_tem_novidade():
    citadas = {e.get("spec") for e in _reais()}
    faltando = []
    for spec in sorted(SPECS.glob("*.md")):
        m = re.match(r"(\d+)", spec.name)
        if not m or int(m.group(1)) < 156:
            continue
        campos = _cabecalho(spec)
        if campos.get("status") != "done":
            continue
        if campos.get("gaveta") not in ("capacidade nova", "experiência"):
            continue
        numero = campos.get("id") or m.group(1)
        if numero not in citadas:
            faltando.append(spec.name)
    assert not faltando, f"spec entregue sem entrada em app/novidades.json: {faltando}"


# --- ?aba= no navegador -----------------------------------------------------------


def _abrir_no_navegador(pagina: str, consulta: str) -> tuple[str | None, list[str]]:
    """Abre a home em `http://painel.teste/<consulta>` e devolve a aba ativa e os erros."""
    from playwright.sync_api import sync_playwright

    sem_scripts = re.sub(r"<script\b[^>]*\bsrc=[^>]*>\s*</script>", "", pagina)
    erros: list[str] = []
    with sync_playwright() as p:
        navegador = p.chromium.launch(
            executable_path=os.environ.get("CHROMIUM_PATH") or None
        )
        try:
            aba = navegador.new_page()

            def _rota(rota) -> None:
                if rota.request.url.startswith("http://painel.teste/"):
                    rota.fulfill(status=200, content_type="text/html", body=sem_scripts)
                else:
                    rota.abort()

            aba.route("**/*", _rota)
            aba.on("pageerror", lambda exc: erros.append(f"pageerror: {exc}"))
            aba.on(
                "console",
                lambda msg: (
                    erros.append(f"console.error: {msg.text}")
                    if msg.type == "error"
                    and not msg.text.startswith("Failed to load resource")
                    else None
                ),
            )
            aba.goto(f"http://painel.teste/{consulta}")
            aba.add_script_tag(content="window.Plotly = {newPlot: function () {}};")
            aba.add_script_tag(content=(STATIC / "ui.js").read_text(encoding="utf-8"))
            aba.evaluate("document.dispatchEvent(new Event('DOMContentLoaded'));")
            aba.wait_for_timeout(200)
            ativa = aba.evaluate(
                "(() => { const b = document.querySelector('.aba-btn.ativo[data-aba]');"
                " return b ? b.getAttribute('data-aba') : null; })()"
            )
        finally:
            navegador.close()
    return ativa, erros


def test_aba_pela_url_no_navegador(exemplo):
    home = client.get("/").text
    ativa, erros = _abrir_no_navegador(home, "?aba=alertas")
    assert ativa == "alertas"
    assert erros == []

    ativa, erros = _abrir_no_navegador(home, "?aba=xyz")
    assert ativa == "visao-geral"
    assert erros == []
