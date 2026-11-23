"""Seletor do tema precisa ter quem o use (spec 192).

O avesso de `tests/test_classes_com_estilo.py` (spec 187): um nome de classe
que aparece em seletor de `app/static/*.css` ou de um `<style>` dos templates
tem de aparecer, como palavra inteira, em algum `.html`, `.js` ou `.py` de
`app/`. Regra sem quem a use engana quem lê o CSS.

Classes montadas em tempo de execução (`f"g-cor-{n}"`, `span-{{ span }}`)
não aparecem literalmente: ficam absolvidas por um prefixo de
`PREFIXOS_DINAMICOS` ou por uma entrada de `SEM_USO_CONHECIDOS`, sempre com o
motivo. Exceção que deixa de valer também reprova até a linha sair.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from pathlib import Path

from tests.test_classes_com_estilo import estilos_dos_templates, seletores_do_css

RAIZ = Path(__file__).resolve().parent.parent
APP = RAIZ / "app"
ESTATICOS = APP / "static"

PREFIXOS_DINAMICOS: dict[str, str] = {
    "g-cor-": 'app/gauge.py:99 e 106 montam f"g-cor-{...}"',
    "span-": "app/templates/componentes.html:4 monta span-{{ span }}",
    "novidade-": "app/templates/novidades.html:19 monta novidade-{{ item.tipo }}",
}

SEM_USO_CONHECIDOS: dict[str, str] = {}

_COMENTARIO = re.compile(r"/\*.*?\*/", re.DOTALL)
_ESTILO = re.compile(r"<style[^>]*>.*?</style>", re.DOTALL | re.IGNORECASE)


def nomes_dos_seletores(css: str) -> set[str]:
    """Passo 1 dos Cálculos: sem comentários, sem declarações, os `.nome`."""
    return seletores_do_css(_COMENTARIO.sub("", css))


def usado(nome: str, texto: str) -> bool:
    """Passo 2: palavra inteira, sem `_` nem `-` colado dos dois lados."""
    return re.search(rf"(?<![\w-]){re.escape(nome)}(?![\w-])", texto) is not None


def sem_uso(nomes: Iterable[str], uso: str) -> set[str]:
    return {nome for nome in nomes if not usado(nome, uso)}


def problemas(
    css: str,
    uso: str,
    prefixos: Mapping[str, str],
    conhecidos: Mapping[str, str],
    origem: str = "app/static/tema.css",
) -> list[str]:
    """Mensagens de falha: seletor morto e exceção vencida."""
    mortos = sem_uso(nomes_dos_seletores(css), uso)
    dinamicos = {n for n in mortos if any(n.startswith(p) for p in prefixos)}
    mensagens = [
        f"seletor .{nome} em {origem} não é usado por nenhum template, JS ou "
        "Python: apague a regra ou registre em SEM_USO_CONHECIDOS com o motivo"
        for nome in sorted(mortos - dinamicos - set(conhecidos))
    ]
    mensagens += [
        f"exceção vencida: `{nome}` não é mais seletor sem uso (aparece "
        "literalmente em app/ ou saiu do CSS); tire a linha de SEM_USO_CONHECIDOS"
        for nome in sorted(set(conhecidos) - mortos)
    ]
    mensagens += [
        f"exceção vencida: nenhum seletor sem uso começa por `{prefixo}`; "
        "tire a linha de PREFIXOS_DINAMICOS"
        for prefixo in sorted(prefixos)
        if not any(n.startswith(prefixo) for n in mortos)
    ]
    return mensagens


def _arquivos_reais() -> tuple[str, str]:
    """CSS (folhas e `<style>` dos templates) e o texto onde procurar o uso."""
    htmls = [p.read_text(encoding="utf-8") for p in sorted(APP.rglob("*.html"))]
    css = "\n".join(
        p.read_text(encoding="utf-8") for p in sorted(ESTATICOS.glob("*.css"))
    )
    css += "\n" + estilos_dos_templates(htmls)
    # O `<style>` do template é CSS, não uso: sem tirá-lo, o seletor se
    # absolveria sozinho.
    uso = [_ESTILO.sub(" ", texto) for texto in htmls]
    uso += [
        p.read_text(encoding="utf-8")
        for extensao in ("*.js", "*.py")
        for p in sorted(APP.rglob(extensao))
    ]
    return css, "\n".join(uso)


def test_todo_seletor_do_tema_tem_quem_o_use():
    css, uso = _arquivos_reais()
    erros = problemas(css, uso, PREFIXOS_DINAMICOS, SEM_USO_CONHECIDOS)
    assert not erros, "\n".join(erros)
