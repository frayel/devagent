"""Aceite da spec 147: os tiles da Maré têm contraste legível.

O teste lê os tokens e a regra `.heatmap-ativo` de `app/static/tema.css` como
estão e calcula, em Python, a razão de contraste WCAG 2.1 entre a cor que o
navegador pinta no texto e o fundo composto do tile, para cada estado que a
fórmula de intensidade produz. Sem rede.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from devagent.aceite import exigir_spec_done

RAIZ = Path(__file__).resolve().parents[1]
TEMA = RAIZ / "app" / "static" / "tema.css"

NOMES_DE_COR = {"white": "#ffffff", "black": "#000000"}

# (token do sinal, |variação| em %) — sinal zero só existe com variação 0.
ESTADOS = [
    ("--alta", 0.1),
    ("--alta", 1.0),
    ("--alta", 5.0),
    ("--alta", 10.0),
    ("--baixa", 0.1),
    ("--baixa", 1.0),
    ("--baixa", 5.0),
    ("--baixa", 10.0),
    ("--borda", 0.0),
]


def _css() -> str:
    return TEMA.read_text(encoding="utf-8")


def _regra_tile() -> str:
    m = re.search(r"(?m)^\.heatmap-ativo\s*\{([^}]*)\}", _css())
    assert m, ".heatmap-ativo não encontrada em tema.css"
    # Comentários não são declarações.
    return re.sub(r"/\*.*?\*/", "", m.group(1), flags=re.S)


def _declaracao(regra: str, prop: str) -> str | None:
    m = re.search(rf"(?:^|;|\s){re.escape(prop)}\s*:\s*([^;]+);", regra)
    return m.group(1).strip() if m else None


def _token(nome: str) -> tuple[int, int, int]:
    m = re.search(rf"{re.escape(nome)}\s*:\s*(#[0-9a-fA-F]{{6}})\s*;", _css())
    assert m, f"token {nome} sem hexadecimal de 6 dígitos em tema.css"
    return _hex(m.group(1))


def _hex(valor: str) -> tuple[int, int, int]:
    v = valor.lstrip("#")
    return (int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16))


def _cor(valor: str) -> tuple[int, int, int]:
    valor = valor.strip()
    if valor in NOMES_DE_COR:
        return _hex(NOMES_DE_COR[valor])
    m = re.fullmatch(r"var\((--[\w-]+)\)", valor)
    if m:
        return _token(m.group(1))
    if re.fullmatch(r"#[0-9a-fA-F]{6}", valor):
        return _hex(valor)
    raise AssertionError(f"cor do texto não reconhecida pelo teste: {valor!r}")


def _luminancia(rgb: tuple[float, float, float]) -> float:
    def canal(c: float) -> float:
        c /= 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (canal(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contraste(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    la, lb = _luminancia(a), _luminancia(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def _mistura(frente, fundo, peso: float) -> tuple[float, float, float]:
    return tuple(peso * f + (1 - peso) * t for f, t in zip(frente, fundo))  # type: ignore[return-value]


def _intensidade(variacao: float) -> float:
    return 0.3 + 0.7 * min(abs(variacao) / 5, 1)


def _fundo(regra: str, cor_sinal, intensidade: float) -> tuple[float, float, float]:
    fundo = _declaracao(regra, "background-color") or _declaracao(regra, "background")
    assert fundo, ".heatmap-ativo sem cor de fundo"
    if fundo == "var(--ativo-cor)":
        return cor_sinal
    m = re.fullmatch(
        r"color-mix\(\s*in\s+srgb\s*,\s*var\(--ativo-cor\)\s+"
        r"calc\(\s*var\(--ativo-opacidade\)\s*\*\s*([\d.]+)%\s*\)\s*,\s*"
        r"var\((--[\w-]+)\)\s*\)",
        fundo,
    )
    assert m, f"fundo de .heatmap-ativo em forma que o teste não modela: {fundo!r}"
    peso = intensidade * float(m.group(1)) / 100
    return _mistura(cor_sinal, _token(m.group(2)), peso)


@pytest.fixture(autouse=True)
def _spec_done():
    exigir_spec_done("147")


def test_tile_nao_declara_opacity():
    regra = _regra_tile()
    assert _declaracao(regra, "opacity") is None, (
        ".heatmap-ativo declara opacity: o texto desbota junto com o fundo"
    )


@pytest.mark.parametrize(("token", "variacao"), ESTADOS)
def test_contraste_do_texto_em_todo_estado(token, variacao):
    regra = _regra_tile()
    superficie = _token("--superficie")
    intensidade = _intensidade(variacao)
    fundo = _fundo(regra, _token(token), intensidade)

    cor_texto = _declaracao(regra, "color")
    assert cor_texto, ".heatmap-ativo sem cor de texto"
    texto: tuple[float, float, float] = _cor(cor_texto)
    opacidade = _declaracao(regra, "opacity")
    if opacidade is not None:  # o texto passa pela mesma composição
        texto = _mistura(texto, superficie, intensidade)

    razao = _contraste(texto, fundo)
    assert razao >= 4.5, f"{token} |var|={variacao}: contraste {razao:.2f}:1"


def test_exemplo_da_spec_com_o_css_antigo_reprovava():
    """O cálculo do teste reproduz o exemplo de ponta a ponta da spec."""
    alta, sup = (63, 182, 139), (18, 24, 33)
    fundo = _mistura(alta, sup, 0.44)
    assert _contraste(_mistura((255, 255, 255), sup, 0.44), fundo) == pytest.approx(
        1.84, abs=0.02
    )
    assert _contraste((255, 255, 255), fundo) == pytest.approx(7.55, abs=0.05)


def test_tile_mostra_o_sinal_junto_do_ticker(setup_db):
    from app.database import MareData, save_mare_data
    from app.main import app

    heatmap = [
        {"ticker": "PETR4", "variacao": 2.5, "financeiro": 1500000, "peso": 0.5},
        {"ticker": "VALE3", "variacao": -1.2, "financeiro": 1000000, "peso": 0.33},
        {"ticker": "ITUB4", "variacao": 0.0, "financeiro": 500000, "peso": 0.17},
    ]
    save_mare_data(
        MareData(
            timestamp=datetime.now(timezone.utc),
            valor=68,
            fluxo=74.0,
            calma=61.0,
            volume=62.0,
            ativos_json=json.dumps(heatmap),
            historico_json="[]",
            fonte="demonstracao",
        )
    )
    html = TestClient(app).get("/").text

    tiles = re.findall(r'class="heatmap-ativo"[^>]*>(.*?)</div>', html, flags=re.S)
    textos = {" ".join(t.split()) for t in tiles}
    assert "▲ PETR4" in textos
    assert "▼ VALE3" in textos
    assert "■ ITUB4" in textos
