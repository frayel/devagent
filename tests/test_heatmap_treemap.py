"""O heatmap da Maré é um treemap: a área do tile é proporcional ao volume.

No layout em linhas da spec 169, os tiles que sobravam na última linha
esticavam até a borda. Como a ordem é do maior volume para o menor, os menores
saíam como os maiores quadros: em 17/11, a 390 px, PRIO3 (5,5% do volume dos
dez) tinha 162 px de largura e PETR4 (18,4%) tinha 98 px.

Roda no Chromium headless, sem internet, com `app/static/tema.css` e
`app/static/ui.js`, como o `tests/test_aceite_169.py`.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from itertools import combinations

import pytest
from fastapi.testclient import TestClient

from tests.test_aceite_169 import EXEMPLO, JANELAS, _pagina, _tile, STATIC

# Os dez do heatmap de produção em 17/11 (ticker, peso, variação).
PRODUCAO_17_11 = [
    ("PETR4", 0.1842, 1.00),
    ("BBAS3", 0.1465, 0.27),
    ("ITUB4", 0.1382, 0.46),
    ("VALE3", 0.1357, 0.61),
    ("B3SA3", 0.0954, 1.55),
    ("WEGE3", 0.0638, 3.13),
    ("BPAC11", 0.0620, 1.44),
    ("SUZB3", 0.0614, 1.17),
    ("BBDC4", 0.0576, 1.76),
    ("PRIO3", 0.0553, 3.00),
]

VAO = 1  # metade do espaço entre tiles, como no ui.js

MEDIR = """() => {
    const h = document.querySelector('.heatmap');
    const c = h.getBoundingClientRect();
    return {
        treemap: h.classList.contains('treemap'),
        cont: {x: c.left, y: c.top, w: c.width, h: c.height},
        tiles: [...h.querySelectorAll('.heatmap-ativo')].map(el => {
            const r = el.getBoundingClientRect();
            return {
                texto: el.textContent.trim(),
                x: r.left, y: r.top, w: r.width, h: r.height,
                sw: el.scrollWidth, cw: el.clientWidth,
                sh: el.scrollHeight, ch: el.clientHeight,
            };
        }),
    };
}"""


def _medir(ativos, janela: int) -> dict:
    from playwright.sync_api import sync_playwright
    import os

    with sync_playwright() as p:
        navegador = p.chromium.launch(
            executable_path=os.environ.get("CHROMIUM_PATH") or None
        )
        try:
            aba = navegador.new_page(viewport={"width": janela, "height": 900})
            aba.route("**/*", lambda rota: rota.abort())
            aba.set_content(_pagina([_tile(*a) for a in ativos]))
            aba.add_script_tag(content=(STATIC / "ui.js").read_text(encoding="utf-8"))
            aba.evaluate("document.dispatchEvent(new Event('DOMContentLoaded'));")
            return aba.evaluate(MEDIR)
        finally:
            navegador.close()


def _area(t: dict) -> float:
    # O ui.js recua cada tile VAO px de cada lado; a fatia dele inclui o recuo.
    return (t["w"] + 2 * VAO) * (t["h"] + 2 * VAO)


@pytest.mark.parametrize("janela", JANELAS)
@pytest.mark.parametrize("ativos", [EXEMPLO, PRODUCAO_17_11], ids=["exemplo", "17-11"])
def test_area_proporcional_ao_volume(ativos, janela):
    m = _medir(ativos, janela)
    assert m["treemap"]
    total_cont = m["cont"]["w"] * m["cont"]["h"]
    soma_pesos = sum(p for _, p, _ in ativos)
    for (ticker, peso, _), t in zip(ativos, m["tiles"]):
        fracao = _area(t) / total_cont
        assert fracao == pytest.approx(peso / soma_pesos, abs=0.006), (ticker, janela)
    areas = [_area(t) for t in m["tiles"]]
    pesos = [p for _, p, _ in ativos]
    ordem_areas = sorted(range(len(areas)), key=lambda i: -areas[i])
    ordem_pesos = sorted(range(len(pesos)), key=lambda i: -pesos[i])
    assert ordem_areas == ordem_pesos


@pytest.mark.parametrize("janela", JANELAS)
def test_tiles_dentro_sem_sobrepor_e_inteiros(janela):
    m = _medir(EXEMPLO, janela)
    c = m["cont"]
    for t in m["tiles"]:
        assert t["x"] >= c["x"] - 0.5 and t["x"] + t["w"] <= c["x"] + c["w"] + 0.5, t
        assert t["y"] >= c["y"] - 0.5 and t["y"] + t["h"] <= c["y"] + c["h"] + 0.5, t
        # Rótulo inteiro: nem o ticker nem a seta cortados.
        assert t["sw"] <= t["cw"] and t["sh"] <= t["ch"], (janela, t)
    for a, b in combinations(m["tiles"], 2):
        dx = min(a["x"] + a["w"], b["x"] + b["w"]) - max(a["x"], b["x"])
        dy = min(a["y"] + a["h"], b["y"] + b["h"]) - max(a["y"], b["y"])
        assert dx <= 0.5 or dy <= 0.5, (a["texto"], b["texto"])


def test_menor_volume_nao_vira_o_maior_quadro():
    """O caso que o usuário viu: a 390 px, PRIO3 era o tile mais largo."""
    m = _medir(PRODUCAO_17_11, 390)
    por_ticker = {t["texto"].split()[-1]: t for t in m["tiles"]}
    assert _area(por_ticker["PRIO3"]) < _area(por_ticker["PETR4"]) / 3
    assert max(m["tiles"], key=_area)["texto"].endswith("PETR4")


def test_legenda_diz_o_que_e_area_e_cor(setup_db):
    from app.database import MareData, save_mare_data
    from app.main import app

    heatmap = [
        {"ticker": t, "variacao": v, "financeiro": p * 1e9, "peso": p}
        for t, p, v in PRODUCAO_17_11
    ]
    save_mare_data(
        MareData(
            timestamp=datetime.now(timezone.utc),
            valor=60,
            fluxo=60.0,
            calma=60.0,
            volume=60.0,
            ativos_json=json.dumps(heatmap),
            historico_json="[]",
            fonte="demonstracao",
        )
    )
    html = TestClient(app).get("/").text
    assert 'class="heatmap-legenda"' in html
    assert "Área: volume financeiro do dia" in html
    assert "cor: variação do preço" in html
