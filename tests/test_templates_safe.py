"""Padrão para HTML montado dentro dos templates (docs/DESIGN.md, seção 7).

Em 15/11/2026 o card Fator Peso Pesado mostrou `<div ...>` como texto:
`('<div>' ~ (frase | e) ~ '</div>') | safe`. Com autoescape, o `~` com um
operando já escapado escapa os literais, e o `| safe` do fim chega tarde. O
inverso, `('<span>' ~ valor ~ '</span>') | safe` com tudo `str`, renderiza,
mas publica `valor` sem escape.

O padrão é um só: cada literal com marcação leva o próprio `| safe`, e o valor
fica de fora, escapado pelo autoescape:

    ('<span>' | safe) ~ valor ~ ('</span>' | safe)

Este teste lê a árvore do Jinja de todo template e reprova:

1. `| safe` aplicado a algo que não seja um literal de texto ou a saída de uma
   macro (concatenação, variável, atributo);
2. literal com `<` ou `>` dentro de uma concatenação sem o próprio `| safe`.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from jinja2 import Environment, nodes

TEMPLATES = Path(__file__).resolve().parents[1] / "app" / "templates"


def _violacoes(fonte: str) -> list[str]:
    arvore = Environment(autoescape=True).parse(fonte)
    achados: list[str] = []
    for filtro in arvore.find_all(nodes.Filter):
        if filtro.name != "safe":
            continue
        alvo = filtro.node
        if isinstance(alvo, nodes.Const) and isinstance(alvo.value, str):
            continue
        if isinstance(alvo, nodes.Call):
            continue
        achados.append(
            f"linha {filtro.lineno}: | safe sobre {type(alvo).__name__}; "
            "aplique | safe só a cada literal com marcação"
        )
    for concat in arvore.find_all(nodes.Concat):
        for parte in concat.nodes:
            if (
                isinstance(parte, nodes.Const)
                and isinstance(parte.value, str)
                and ("<" in parte.value or ">" in parte.value)
            ):
                achados.append(
                    f"linha {concat.lineno}: literal {parte.value[:40]!r} com "
                    "marcação numa concatenação sem o próprio | safe"
                )
    return achados


@pytest.mark.parametrize(
    "template", sorted(p.name for p in TEMPLATES.glob("*.html")), ids=str
)
def test_template_segue_o_padrao_do_safe(template):
    fonte = (TEMPLATES / template).read_text(encoding="utf-8")
    assert _violacoes(fonte) == []


@pytest.mark.parametrize(
    "trecho",
    [
        # O defeito de 15/11/2026.
        """{{ ('<div class="x">' ~ (frase | e) ~ '</div>') | safe }}""",
        # Valor publicado sem escape.
        """{{ ('<span>' ~ valor ~ '</span>') | safe }}""",
        """{% set v = ('<span>R$ ' ~ preco ~ '</span>') %}{{ v | safe }}""",
        # Literal com marcação sem | safe: vira texto na tela.
        """{{ ('<b>' | safe) ~ valor ~ '</b>' }}""",
        # Fim de abertura de tag sem | safe: o `">` vira texto.
        """{{ ('<span class="' | safe) ~ classe ~ '">' ~ valor ~ ('</span>' | safe) }}""",
    ],
)
def test_detecta_os_padroes_proibidos(trecho):
    assert _violacoes(trecho)


@pytest.mark.parametrize(
    "trecho",
    [
        """{{ ('<span>' | safe) ~ valor ~ ('</span>' | safe) }}""",
        """{{ ('<div class="x">' | safe) ~ (frase | e) ~ ('</div>' | safe) }}""",
        """{{ '<p class="sub">Texto fixo</p>' | safe }}""",
        """{% macro m(x) %}<i>{{ x }}</i>{% endmacro %}{{ m(1) | safe }}""",
        """{{ 'perto da mínima (<=2%)' }}""",
    ],
)
def test_aceita_o_padrao(trecho):
    assert _violacoes(trecho) == []
