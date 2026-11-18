"""Aceite da spec 181: o gráfico do Ibovespa avisa quando a biblioteca não carregou."""

from __future__ import annotations

import html as html_mod
import json
import os
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.database import IbovespaData, save_ibovespa_data
from app.main import app
from devagent.aceite import exigir_spec_done

BRT = timezone(timedelta(hours=-3))
STATIC = Path(__file__).resolve().parents[1] / "app" / "static"
client = TestClient(app)

PRIMEIRO = 210000.0
PENULTIMO = 165967.33
ULTIMO = 167627.0

AVISO = "Gráfico indisponível agora."
SERVIDOS = {
    "/static/graficos.js": ("application/javascript", "graficos.js"),
    "/static/ui.js": ("application/javascript", "ui.js"),
    "/static/tema.css": ("text/css", "tema.css"),
}


def test_aceite_181_spec_done():
    exigir_spec_done("181")


# Helpers copiados de tests/test_aceite_145.py: 30 pregões gravados no banco.


def _datas() -> list[str]:
    feriados = {date(2026, 10, 12), date(2026, 11, 2)}
    d, fim, out = date(2026, 9, 23), date(2026, 11, 5), []
    while d <= fim:
        if d.weekday() < 5 and d not in feriados:
            out.append(d.isoformat())
        d += timedelta(days=1)
    assert len(out) == 30
    return out


def _fechamentos() -> list[float]:
    passo = (PRIMEIRO - PENULTIMO) / 28
    meio = [round(PRIMEIRO - passo * i, 2) for i in range(29)]
    meio[-1] = PENULTIMO
    return meio + [ULTIMO]


@pytest.fixture
def relogio(monkeypatch):
    class Relogio(datetime):
        agora: datetime = datetime(2026, 11, 5, 18, 30, tzinfo=BRT)

        @classmethod
        def now(cls, tz=None):  # type: ignore[override]
            return cls.agora if tz is None else cls.agora.astimezone(tz)

    monkeypatch.setattr("app.main.datetime", Relogio)
    return Relogio


def _gravar() -> None:
    save_ibovespa_data(
        IbovespaData(
            timestamp=datetime(2026, 11, 5, 18, 0, tzinfo=BRT).astimezone(timezone.utc),
            current_price=ULTIMO,
            previous_close=PENULTIMO,
            history_json=json.dumps({"dates": _datas(), "closes": _fechamentos()}),
            fonte="yfinance",
        )
    )


def _aria_label_do_servidor(pagina: str) -> str:
    m = re.search(r'<div id="grafico-ibovespa".*?>', pagina, re.S)
    assert m, "gráfico do Ibovespa não encontrado na home"
    rotulo = re.search(r"""aria-label=(['"])(.*?)\1""", m.group(0), re.S)
    assert rotulo, "aria-label ausente no gráfico"
    return html_mod.unescape(rotulo.group(2))


def _abrir(pagina: str, init_script: str | None) -> tuple[dict, list[str]]:
    """Abre a home com os scripts da página intactos e a CDN abortada."""
    from playwright.sync_api import sync_playwright

    erros: list[str] = []
    with sync_playwright() as p:
        navegador = p.chromium.launch(
            executable_path=os.environ.get("CHROMIUM_PATH") or None
        )
        try:
            aba = navegador.new_page()

            def _rota(rota) -> None:
                url = rota.request.url
                if not url.startswith("http://painel.teste/"):
                    rota.abort()
                    return
                caminho = url[len("http://painel.teste") :].split("?")[0]
                if caminho == "/":
                    rota.fulfill(status=200, content_type="text/html", body=pagina)
                elif caminho in SERVIDOS:
                    tipo, nome = SERVIDOS[caminho]
                    corpo = (STATIC / nome).read_text(encoding="utf-8")
                    rota.fulfill(status=200, content_type=tipo, body=corpo)
                else:
                    rota.abort()

            aba.route("**/*", _rota)
            aba.on("pageerror", lambda exc: erros.append(f"pageerror: {exc}"))
            if init_script:
                aba.add_init_script(init_script)
            aba.goto("http://painel.teste/", wait_until="load")
            aba.wait_for_timeout(200)
            estado = aba.evaluate(
                """() => {
                    const el = document.getElementById('grafico-ibovespa');
                    return {
                        texto: el.textContent,
                        aviso: !!el.querySelector('.grafico-indisponivel'),
                        desenhado: el.dataset.desenhado || null,
                        role: el.getAttribute('role'),
                        aria: el.getAttribute('aria-label'),
                    };
                }"""
            )
        finally:
            navegador.close()
    return estado, erros


@pytest.fixture
def home(relogio) -> str:
    _gravar()
    resposta = client.get("/")
    assert resposta.status_code == 200
    return resposta.text


def _papel_e_rotulo_intactos(estado: dict, pagina: str) -> None:
    assert estado["role"] == "img"
    assert estado["aria"] == _aria_label_do_servidor(pagina)


def test_cdn_bloqueada_mostra_aviso_sem_erro(home):
    estado, erros = _abrir(home, None)
    assert AVISO in estado["texto"]
    assert estado["aviso"] is True
    assert erros == []
    _papel_e_rotulo_intactos(estado, home)


def test_plotly_presente_desenha_sem_aviso(home):
    estado, erros = _abrir(
        home,
        "window.Plotly = {newPlot: (id) => {"
        " document.getElementById(id).dataset.desenhado = '1'; return Promise.resolve(); }};",
    )
    assert estado["desenhado"] == "1"
    assert "Gráfico indisponível" not in estado["texto"]
    assert estado["aviso"] is False
    assert erros == []
    _papel_e_rotulo_intactos(estado, home)


def test_newplot_rejeitado_mostra_aviso(home):
    estado, _erros = _abrir(
        home, "window.Plotly = {newPlot: () => Promise.reject(new Error('x'))};"
    )
    assert AVISO in estado["texto"]
    assert estado["aviso"] is True
    _papel_e_rotulo_intactos(estado, home)
