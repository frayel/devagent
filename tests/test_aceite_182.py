"""Aceite da spec 182: o seletor da Maré mostra que está carregando.

Sem internet. A leitura e o histórico da Maré são os de
`tests/test_aceite_174b.py` (Marolas 68, Ondas 51, Maré 32). As páginas e os
fragmentos são gerados antes de abrir o navegador, pelo `TestClient`, e o
Chromium do ambiente os recebe por `route`, com o atraso de cada cenário. A API
assíncrona do Playwright deixa o atraso correr sem travar as medições na
página. O Chromium ausente faz o teste falhar, não pular (padrão da 146).
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import re
from urllib.parse import parse_qs, urlsplit

from fastapi.testclient import TestClient

from devagent.aceite import exigir_spec_done
from tests.test_aceite_174b import (  # noqa: F401  (fixtures)
    MARE,
    ONDAS,
    calendario_fixo,
    com_historico,
    com_mare,
)

BASE = "http://painel.teste"
CORPO = ".painel-mare .mare-corpo"
GAUGE = ".painel-mare .g-centro .v"


def test_aceite_182_spec_done():
    exigir_spec_done("182")


def _respostas() -> dict[str, tuple[int, str, bytes]]:
    from app.main import app as aplicacao

    cliente = TestClient(aplicacao)
    caminhos = [
        "/mare",
        "/mare?nivel=ondas",
        "/mare/card?nivel=ondas",
        "/mare/card?nivel=mare",
    ]
    caminhos += [f"/static/{n}" for n in ("tema.css", "ui.js", "graficos.js")]
    saida = {}
    for caminho in caminhos:
        r = cliente.get(caminho)
        saida[caminho] = (
            r.status_code,
            r.headers.get("content-type", "text/html"),
            r.content,
        )
    return saida


def _rodar(cenario, atrasos=None, status=None, reduzido=False) -> dict:
    """Abre `/mare` no Chromium e roda `cenario(aba, registro)`.

    `atrasos` e `status` são por nível de `/mare/card`. O registro guarda os
    pedidos a `/mare/card` e os que falharam (abortados pelo `ui.js`).
    """
    from playwright.async_api import Error as ErroPlaywright
    from playwright.async_api import async_playwright

    respostas = _respostas()
    atrasos = atrasos or {}
    status = status or {}
    registro: dict = {"pedidos": [], "falhas": [], "erros": []}

    async def servir(rota) -> None:
        url = urlsplit(rota.request.url)
        if f"{url.scheme}://{url.netloc}" != BASE:
            await rota.abort()
            return
        caminho = url.path + (f"?{url.query}" if url.query else "")
        if url.path == "/mare/card":
            nivel = parse_qs(url.query)["nivel"][0]
            registro["pedidos"].append(nivel)
            await asyncio.sleep(atrasos.get(nivel, 0))
            if nivel in status:
                with contextlib.suppress(ErroPlaywright):
                    await rota.fulfill(status=status[nivel], body="erro")
                return
        if caminho not in respostas:
            await rota.fulfill(status=404, body="")
            return
        codigo, tipo, corpo = respostas[caminho]
        # O pedido pode ter sido abortado pela página enquanto esperava.
        with contextlib.suppress(ErroPlaywright):
            await rota.fulfill(
                status=codigo, headers={"content-type": tipo}, body=corpo
            )

    async def principal() -> dict:
        async with async_playwright() as p:
            navegador = await p.chromium.launch(
                executable_path=os.environ.get("CHROMIUM_PATH") or None
            )
            try:
                contexto = await navegador.new_context(
                    reduced_motion="reduce" if reduzido else "no-preference"
                )
                aba = await contexto.new_page()
                await aba.route("**/*", servir)
                aba.on("pageerror", lambda exc: registro["erros"].append(str(exc)))
                aba.on(
                    "requestfailed",
                    lambda req: registro["falhas"].append(req.url),
                )
                await aba.goto(f"{BASE}/mare")
                registro["resultado"] = await cenario(aba, registro)
            finally:
                await navegador.close()
        return registro

    return asyncio.run(principal())


async def _esperar_gauge(aba, valor: int) -> None:
    await aba.wait_for_function(
        f"document.querySelector('{GAUGE}').textContent.trim() === '{valor}'"
    )


ESTADO_JS = """() => {
    const corpo = document.querySelector('.painel-mare .mare-corpo');
    const op = n => corpo.querySelector(`.mare-nivel a[data-nivel="${n}"]`);
    return {
        ondas_atual: op('ondas').getAttribute('aria-current'),
        ondas_busy: op('ondas').getAttribute('aria-busy'),
        ondas_carregando: op('ondas').classList.contains('carregando'),
        marolas_atual: op('marolas').getAttribute('aria-current'),
        corpo_busy: corpo.getAttribute('aria-busy'),
    };
}"""

CLICAR_ONDAS_JS = """async () => {
    const t0 = performance.now();
    document.querySelector('.mare-nivel a[data-nivel="ondas"]').click();
    const quadro = (%s)();
    await new Promise(r => setTimeout(r, 100));
    return { quadro, cem: (%s)(), ms: performance.now() - t0 };
}""".replace("%s", ESTADO_JS)


def test_feedback_imediato_e_fim_da_carga(com_historico):  # noqa: F811
    async def cenario(aba, _):
        medido = await aba.evaluate(CLICAR_ONDAS_JS)
        await _esperar_gauge(aba, ONDAS)
        medido["depois"] = await aba.evaluate(
            """() => {
                const card = document.querySelector('.painel-mare');
                return {
                    busy: card.querySelectorAll('[aria-busy]').length,
                    carregando: card.querySelectorAll('.carregando').length,
                    atualizando: card.querySelectorAll('.atualizando').length,
                };
            }"""
        )
        return medido

    r = _rodar(cenario, atrasos={"ondas": 1.0})
    for momento in ("quadro", "cem"):
        estado = r["resultado"][momento]
        assert estado["ondas_atual"] == "true", (momento, estado)
        assert estado["ondas_busy"] == "true", (momento, estado)
        assert estado["ondas_carregando"] is True, (momento, estado)
        assert estado["marolas_atual"] is None, (momento, estado)
        assert estado["corpo_busy"] == "true", (momento, estado)
    assert r["resultado"]["depois"] == {"busy": 0, "carregando": 0, "atualizando": 0}
    assert r["erros"] == []


OBSERVAR_JS = """() => {
    window.__esmaeceu = false;
    const corpo = document.querySelector('.painel-mare .mare-corpo');
    new MutationObserver(() => {
        if (corpo.classList.contains('atualizando')) window.__esmaeceu = true;
    }).observe(corpo, { attributes: true, attributeFilter: ['class'] });
    corpo.querySelector('.mare-nivel a[data-nivel="ondas"]').click();
}"""


def test_resposta_rapida_nao_esmaece(com_historico):  # noqa: F811
    async def cenario(aba, _):
        await aba.evaluate(OBSERVAR_JS)
        await _esperar_gauge(aba, ONDAS)
        return await aba.evaluate("window.__esmaeceu")

    r = _rodar(cenario, atrasos={"ondas": 0.05})
    assert r["resultado"] is False
    assert r["erros"] == []


def test_resposta_lenta_esmaece_o_card_e_nao_o_seletor(com_historico):  # noqa: F811
    async def cenario(aba, _):
        await aba.evaluate(OBSERVAR_JS)
        await aba.wait_for_timeout(450)
        opacidades = await aba.evaluate(
            """() => {
                // Opacidade efetiva: o produto da do elemento com a dos ancestrais.
                const efetiva = el => {
                    let o = 1;
                    for (; el && el.nodeType === 1; el = el.parentElement) {
                        o *= parseFloat(getComputedStyle(el).opacity);
                    }
                    return o;
                };
                return {
                    centro: efetiva(document.querySelector('.painel-mare .g-centro')),
                    seletor: efetiva(document.querySelector('.painel-mare .mare-nivel')),
                };
            }"""
        )
        esmaeceu = await aba.evaluate("window.__esmaeceu")
        await _esperar_gauge(aba, ONDAS)
        return {"esmaeceu": esmaeceu, **opacidades}

    r = _rodar(cenario, atrasos={"ondas": 1.0})
    assert r["resultado"]["esmaeceu"] is True
    assert r["resultado"]["centro"] < 1
    assert r["resultado"]["seletor"] == 1


def test_ultimo_clique_vence(com_historico):  # noqa: F811
    async def cenario(aba, _):
        await aba.evaluate(
            """async () => {
                const op = n => document.querySelector(`.mare-nivel a[data-nivel="${n}"]`);
                op('ondas').click();
                await new Promise(r => setTimeout(r, 100));
                op('mare').click();
            }"""
        )
        await _esperar_gauge(aba, MARE)
        # Tempo de sobra para a resposta de Ondas (1 s) chegar, se não fosse abortada.
        await aba.wait_for_timeout(1300)
        return {
            "gauge": (await aba.inner_text(GAUGE)).strip(),
            "ativo": await aba.get_attribute(
                '.mare-nivel a[aria-current="true"]', "data-nivel"
            ),
            "busy": await aba.evaluate(
                "document.querySelectorAll('.painel-mare [aria-busy]').length"
            ),
        }

    r = _rodar(cenario, atrasos={"ondas": 1.0, "mare": 0.2})
    assert r["resultado"] == {"gauge": str(MARE), "ativo": "mare", "busy": 0}
    assert any("/mare/card?nivel=ondas" in u for u in r["falhas"]), r["falhas"]
    assert r["erros"] == []


def test_clique_repetido_gera_um_pedido(com_historico):  # noqa: F811
    async def cenario(aba, _):
        await aba.evaluate(
            """() => {
                const ondas = document.querySelector('.mare-nivel a[data-nivel="ondas"]');
                ondas.click();
                ondas.click();
            }"""
        )
        await _esperar_gauge(aba, ONDAS)

    r = _rodar(cenario, atrasos={"ondas": 0.5})
    assert r["pedidos"] == ["ondas"]


def test_erro_recarrega_a_pagina_com_o_nivel(com_historico):  # noqa: F811
    async def cenario(aba, _):
        await aba.click('.mare-nivel a[data-nivel="ondas"]')
        await aba.wait_for_url(re.compile(r"\?nivel=ondas$"))
        await _esperar_gauge(aba, ONDAS)
        return aba.url

    r = _rodar(cenario, status={"ondas": 500})
    assert parse_qs(urlsplit(r["resultado"]).query)["nivel"] == ["ondas"]


ANIMACAO_JS = """async () => {
    const ondas = document.querySelector('.mare-nivel a[data-nivel="ondas"]');
    ondas.click();
    return getComputedStyle(ondas, '::after').animationName;
}"""


def test_movimento_reduzido_para_o_anel(com_historico):  # noqa: F811
    async def cenario(aba, _):
        return await aba.evaluate(ANIMACAO_JS)

    assert _rodar(cenario, atrasos={"ondas": 1.0}, reduzido=True)["resultado"] == "none"
    # Sem a preferência, o anel gira: a medida acima não passa por acaso.
    assert _rodar(cenario, atrasos={"ondas": 1.0})["resultado"] == "mare-girar"


def test_anuncio_na_regiao_viva_persistente(com_historico):  # noqa: F811
    async def cenario(aba, _):
        antes = await aba.evaluate(
            """() => {
                const regiao = document.querySelector('.painel-mare [aria-live="polite"]');
                regiao.__marca182 = 'mesmo nó';
                document.querySelector('.mare-nivel a[data-nivel="ondas"]').click();
                return regiao.textContent;
            }"""
        )
        await _esperar_gauge(aba, ONDAS)
        depois = await aba.evaluate(
            """() => {
                const regiao = document.querySelector('.painel-mare [aria-live="polite"]');
                return {
                    texto: regiao.textContent,
                    marca: regiao.__marca182 || null,
                    fora_do_corpo: !regiao.closest('.mare-corpo'),
                    regioes: document.querySelectorAll('.painel-mare [aria-live]').length,
                };
            }"""
        )
        return {"antes": antes, **depois}

    r = _rodar(cenario, atrasos={"ondas": 0.3})["resultado"]
    assert r["antes"] == "Carregando Ondas"
    assert r == {
        "antes": "Carregando Ondas",
        "texto": f"Ondas: {ONDAS}, Neutro",
        "marca": "mesmo nó",
        "fora_do_corpo": True,
        "regioes": 1,
    }


# --- HTML do servidor (invariantes de produção) --------------------------------


def _get(caminho: str) -> str:
    from app.main import app as aplicacao

    resposta = TestClient(aplicacao).get(caminho)
    assert resposta.status_code == 200
    return resposta.text


def test_regiao_viva_no_card_fora_do_corpo(com_historico):  # noqa: F811
    for caminho in ("/mare", "/"):
        html = _get(caminho)
        card = re.search(
            r'<section class="painel[^"]*\bpainel-mare\b[^"]*">(.*?)</section>',
            html,
            re.DOTALL,
        )
        assert card, caminho
        regiao = re.search(
            r'<p class="so-leitor mare-anuncio" aria-live="polite"></p>', card.group(1)
        )
        assert regiao, caminho
        # Fica depois do fechamento do .mare-corpo, que é o único div antes dele
        # no mesmo nível: a região não está dentro do conteúdo trocado.
        antes = card.group(1)[: regiao.start()]
        assert antes.count("<div") == antes.count("</div>"), caminho


def test_fragmento_traz_data_anuncio(com_historico):  # noqa: F811
    html = _get("/mare/card?nivel=ondas")
    m = re.search(r'<div class="mare-corpo" data-anuncio="([^"]*)"', html)
    assert m and m.group(1) == f"Ondas: {ONDAS}, Neutro"
    m = re.search(
        r'<div class="mare-corpo" data-anuncio="([^"]*)"', _get("/mare/card?nivel=mare")
    )
    assert m and m.group(1) == f"Maré: {MARE}, Medo"


def test_anuncio_em_formacao(com_mare):  # noqa: F811
    m = re.search(
        r'<div class="mare-corpo" data-anuncio="([^"]*)"',
        _get("/mare/card?nivel=ondas"),
    )
    assert m and m.group(1) == "Ondas: histórico em formação"


def test_sem_estilo_inline_novo():
    from pathlib import Path

    raiz = Path(__file__).resolve().parents[1]
    js = (raiz / "app" / "static" / "ui.js").read_text(encoding="utf-8")
    inicio = js.index("// Carga do card (spec 182)")
    trecho = js[inicio : js.index("// Pedido trocado por um clique mais novo", inicio)]
    assert ".style" not in trecho
    assert "MARE_DESISTIR_MS = 8000" in js
