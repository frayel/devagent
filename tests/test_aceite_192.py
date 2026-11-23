"""Aceite da spec 192: seletor do tema que nada usa reprova o teste.

Sem rede e sem servidor: as funções puras de `tests/test_seletores_usados.py`
com textos montados aqui, e a regra rodada contra os arquivos reais.
"""

from __future__ import annotations

import pytest

from devagent.aceite import exigir_spec_done
from tests import test_classes_com_estilo as t187
from tests.test_seletores_usados import (
    PREFIXOS_DINAMICOS,
    RAIZ,
    SEM_USO_CONHECIDOS,
    _arquivos_reais,
    nomes_dos_seletores,
    problemas,
    sem_uso,
)

PREFIXO_GAUGE = {"g-cor-": "app/gauge.py monta f'g-cor-{n}'"}
MORTAS_DA_SPEC = {
    "pilha",
    "m-t-2",
    "d-block",
    "painel-estado-container",
    "painel-tendencia",
    "painel-apetite",
    "painel-rotacao",
    "texto-num",
    "tabela-scroll",
}


@pytest.fixture(autouse=True)
def _so_com_a_spec_done():
    exigir_spec_done("192")


def _acusados(css: str, uso: str, conhecidos: dict[str, str] | None = None) -> set[str]:
    return (
        sem_uso(nomes_dos_seletores(css), uso)
        - {n for n in nomes_dos_seletores(css) if n.startswith("g-cor-")}
        - set(conhecidos or {})
    )


def test_acusa_a_morta_e_so_ela():
    css = ".usada { } .morta { } .g-cor-3 { }"
    uso = '<div class="usada">'
    erros = problemas(css, uso, PREFIXO_GAUGE, {})
    assert erros == [
        (
            "seletor .morta em app/static/tema.css não é usado por nenhum template, "
            "JS ou Python: apague a regra ou registre em SEM_USO_CONHECIDOS com o motivo"
        )
    ]


def test_palavra_inteira_nao_prefixo():
    css = ".painel-apetite { }"
    uso = '<section class="painel painel-apetite-rotacao">'
    assert _acusados(css, uso) == {"painel-apetite"}


def test_seletor_dentro_de_media_e_colhido():
    css = "@media (max-width: 600px) { .morta { color: red; } }"
    assert _acusados(css, "") == {"morta"}


@pytest.mark.parametrize(
    "uso",
    [
        'classe = f"texto-alta"',
        'classe = "texto-alta"',
        "el.classList.add('texto-alta');",
    ],
)
def test_citada_em_py_ou_js_conta_como_usada(uso):
    assert _acusados(".texto-alta { }", uso) == set()


def test_excecao_vencida_reprova():
    # O nome passou a aparecer literalmente.
    erros = problemas(".x { }", '<b class="x">', {}, {"x": "motivo"})
    assert any("exceção vencida: `x`" in e for e in erros)
    # O seletor saiu do CSS.
    erros = problemas(".y { }", '<b class="y">', {}, {"sumiu": "motivo"})
    assert any("exceção vencida: `sumiu`" in e for e in erros)


def test_repositorio_real_sem_seletor_morto():
    css, uso = _arquivos_reais()
    assert problemas(css, uso, PREFIXOS_DINAMICOS, SEM_USO_CONHECIDOS) == []


def test_as_nove_mortas_sairam_do_tema():
    tema = (RAIZ / "app" / "static" / "tema.css").read_text(encoding="utf-8")
    assert not nomes_dos_seletores(tema) & MORTAS_DA_SPEC
    assert "body.modo-so-sinais .visao-macro:not(.painel-ibovespa) {" in tema


def test_spec_187_continua_valendo_sem_mudar_a_lista():
    templates, css, js = t187._arquivos_reais()
    usos = t187.classes_dos_templates(templates)
    assert t187.problemas(usos, css, js, t187.SEM_ESTILO_CONHECIDAS) == []
    assert len(t187.SEM_ESTILO_CONHECIDAS) == 25
