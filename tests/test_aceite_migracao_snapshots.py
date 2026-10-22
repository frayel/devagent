"""Aceite das specs de migração para `snapshots_paineis` (074, 075a/b, 076a/b).

Cada spec lista no cabeçalho, em `tabelas_legadas:`, as tabelas do SQLite que
deixa de usar. Enquanto a spec não é `done`, o teste dela pula; quando ela
fecha, nenhuma dessas tabelas pode continuar sendo criada, gravada ou lida em
`app/`. A 074 foi marcada `done` com as treze tabelas ainda no `init_db`, e
nada reprovou (ADR 018 do núcleo).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from devagent.aceite import exigir_spec_done

RAIZ = Path(__file__).resolve().parent.parent
CAMPO = re.compile(r"^tabelas_legadas:\s*(.+?)\s*$", re.MULTILINE)
ID = re.compile(r"^id:\s*(\S+)\s*$", re.MULTILINE)


def _specs_de_migracao() -> list[tuple[str, str]]:
    pares = []
    for spec in sorted((RAIZ / "docs" / "specs").rglob("*.md")):
        texto = spec.read_text(encoding="utf-8")
        campo = CAMPO.search(texto)
        if not campo:
            continue
        spec_id = ID.search(texto)
        numero = spec_id.group(1) if spec_id else spec.name.split("-")[0]
        for tabela in re.split(r"[,\s]+", campo.group(1)):
            if tabela:
                pares.append((numero, tabela))
    return pares


def _codigo_do_app() -> dict[str, str]:
    return {
        p.relative_to(RAIZ).as_posix(): p.read_text(encoding="utf-8")
        for p in (RAIZ / "app").rglob("*")
        if p.suffix in {".py", ".html", ".sql"}
    }


CODIGO = _codigo_do_app()


def test_ha_specs_de_migracao() -> None:
    assert _specs_de_migracao(), "nenhuma spec traz `tabelas_legadas:`"


@pytest.mark.parametrize(("spec", "tabela"), _specs_de_migracao())
def test_tabela_legada_saiu_do_app(spec: str, tabela: str) -> None:
    exigir_spec_done(spec)
    padrao = re.compile(rf"\b{re.escape(tabela)}\b")
    onde = sorted(caminho for caminho, texto in CODIGO.items() if padrao.search(texto))
    assert not onde, (
        f"A spec {spec} está done, mas `{tabela}` ainda aparece em {onde}. "
        "Grave e leia o painel por gravar_snapshot/ler_snapshot e apague a "
        "criação da tabela no init_db."
    )
