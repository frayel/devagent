"""Aceite da spec 169: os tiles do heatmap mostram o nome do ativo inteiro.

Roda no Chromium headless, como o da spec 156, sem internet: a página é
montada aqui com `app/static/tema.css` e os tiles do heatmap no mesmo formato do
`index.html`, e as variáveis dos tiles vêm do próprio `app/static/ui.js`. O
contêiner tem a largura da janela menos 16 px (8 px de cada lado).
"""

from __future__ import annotations

import html
import os
from pathlib import Path

import pytest

from devagent.aceite import exigir_spec_done

RAIZ = Path(__file__).resolve().parents[1]
STATIC = RAIZ / "app" / "static"

EXEMPLO = [
    ("PETR4", 0.22, 1.2),
    ("VALE3", 0.20, -0.8),
    ("ITUB4", 0.15, 0.4),
    ("BBDC4", 0.10, -2.1),
    ("BOVA11", 0.09, 0.9),
    ("ABEV3", 0.07, 0.0),
    ("B3SA3", 0.06, 3.5),
    ("WEGE3", 0.05, -0.3),
    ("KLBN11", 0.04, 1.7),
    ("RENT3", 0.02, -5.2),
]

JANELAS = [360, 390, 768, 1280]


def test_aceite_169_spec_done():
    exigir_spec_done("169")


def _tile(ticker: str, peso: float, variacao: float, seta: str | None = None) -> str:
    cor = (
        "var(--alta)"
        if variacao > 0
        else "var(--baixa)"
        if variacao < 0
        else "var(--borda)"
    )
    if seta is None:
        seta = "▲" if variacao > 0 else "▼" if variacao < 0 else "■"
    opacidade = 0.3 + 0.7 * min(abs(variacao) / 5, 1)
    return (
        f'<div title="{html.escape(ticker)}" class="heatmap-ativo" data-peso="{peso}"'
        f' data-cor="{cor}" data-opacidade="{opacidade}">{seta} {html.escape(ticker)}</div>'
    )


def _pagina(tiles: list[str]) -> str:
    css = (STATIC / "tema.css").read_text(encoding="utf-8")
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<style>{css}</style><style>.moldura {{ margin: 0 8px; }}</style>"
        "</head><body><div class='moldura'><div class='heatmap'>"
        + "".join(tiles)
        + "</div></div></body></html>"
    )


MEDIR = """() => {
    const c = document.querySelector('.heatmap').getBoundingClientRect();
    const tiles = [...document.querySelectorAll('.heatmap-ativo')].map(el => {
        const r = el.getBoundingClientRect();
        return {
            texto: el.textContent.trim(),
            esquerda: r.left, direita: r.right, topo: r.top, largura: r.width,
            scroll: el.scrollWidth, cliente: el.clientWidth,
            ch: (() => {
                const s = document.createElement('span');
                s.style.cssText = 'display:inline-block;width:10ch;font:inherit;padding:0';
                el.appendChild(s);
                const w = s.getBoundingClientRect().width;
                s.remove();
                return w;
            })(),
        };
    });
    return {contEsq: c.left, contDir: c.right, largura: c.width, tiles};
}"""


def _medir(tiles: list[str], janela: int, com_js: bool = True) -> dict:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        navegador = p.chromium.launch(
            executable_path=os.environ.get("CHROMIUM_PATH") or None
        )
        try:
            aba = navegador.new_page(viewport={"width": janela, "height": 800})
            aba.route("**/*", lambda rota: rota.abort())
            aba.set_content(_pagina(tiles))
            if com_js:
                aba.add_script_tag(
                    content=(STATIC / "ui.js").read_text(encoding="utf-8")
                )
                aba.evaluate("document.dispatchEvent(new Event('DOMContentLoaded'));")
            return aba.evaluate(MEDIR)
        finally:
            navegador.close()


def _linhas(medida: dict) -> list[list[dict]]:
    linhas: list[list[dict]] = []
    for t in medida["tiles"]:
        if linhas and abs(linhas[-1][0]["topo"] - t["topo"]) < 1:
            linhas[-1].append(t)
        else:
            linhas.append([t])
    return linhas


def _sem_corte(medida: dict) -> None:
    for t in medida["tiles"]:
        assert t["scroll"] <= t["cliente"], t


@pytest.mark.parametrize("janela", JANELAS)
def test_tiles_inteiros_e_linhas_preenchidas(janela):
    medida = _medir([_tile(*a) for a in EXEMPLO], janela)
    assert abs(medida["largura"] - (janela - 16)) <= 1
    _sem_corte(medida)
    for t in medida["tiles"]:
        assert t["largura"] >= t["ch"] - 1, t
    linhas = _linhas(medida)
    for linha in linhas:
        ocupado = sum(t["largura"] for t in linha) + 2 * (len(linha) - 1)
        assert abs(ocupado - medida["largura"]) <= 1, (
            janela,
            [t["texto"] for t in linha],
        )
    if janela >= 768:
        assert len(linhas) == 1
    else:
        assert len(linhas) <= 3
    if janela == 1280:
        larguras = [t["largura"] for t in medida["tiles"][:5]]
        assert larguras == sorted(larguras, reverse=True)


def test_tickers_largos_e_outras_setas_a_360():
    ativos = list(EXEMPLO)
    ativos[0] = ("TAEE11", 0.22, 1.2)
    ativos[2] = ("KLBN11", 0.15, 0.4)
    setas = ["▼", "■"]
    tiles = [_tile(t, p, v, setas[i % 2]) for i, (t, p, v) in enumerate(ativos)]
    _sem_corte(_medir(tiles, 360))


def test_sem_javascript_tiles_iguais_e_inteiros():
    medida = _medir([_tile(*a) for a in EXEMPLO], 390, com_js=False)
    _sem_corte(medida)
    larguras = [t["largura"] for t in medida["tiles"]]
    assert max(larguras) - min(larguras) <= 1, larguras


def test_ticker_de_nove_caracteres_nao_vaza():
    ativos = list(EXEMPLO)
    ativos[4] = ("ABCDEFGHI", 0.09, 0.9)
    medida = _medir([_tile(*a) for a in ativos], 360)
    for t in medida["tiles"]:
        assert t["direita"] <= medida["contDir"] + 0.5, t
