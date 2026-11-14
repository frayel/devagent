"""Toda variável de ambiente lida pelo núcleo está documentada no OPERACAO.md.

O checklist do CICLO.md (seção 5) pede que toda variável nova seja documentada;
`CHROMIUM_PATH` e `JULES_SOURCE` escaparam. Este teste transforma o pedido em
checagem.
"""

from __future__ import annotations

import re
from pathlib import Path

NUCLEO = Path(__file__).resolve().parents[1]
OPERACAO = NUCLEO / "OPERACAO.md"

LEITURA = re.compile(
    r"""(?:environ(?:\.get)?\s*[\[(]|getenv\()\s*["']([A-Z][A-Z0-9_]+)["']"""
)


def variaveis_lidas() -> dict[str, list[str]]:
    achadas: dict[str, list[str]] = {}
    for arquivo in sorted(NUCLEO.rglob("*.py")):
        if "tests" in arquivo.relative_to(NUCLEO).parts:
            continue
        for nome in LEITURA.findall(arquivo.read_text(encoding="utf-8")):
            achadas.setdefault(nome, []).append(str(arquivo.relative_to(NUCLEO)))
    return achadas


def test_regex_encontra_as_leituras_conhecidas():
    lidas = variaveis_lidas()
    assert "RENDER_API_KEY" in lidas
    assert "DEVAGENT_CONFIG" in lidas


def test_toda_variavel_do_nucleo_esta_no_operacao():
    texto = OPERACAO.read_text(encoding="utf-8")
    secao = texto.split("## Secrets e variáveis do núcleo", 1)[1].split("\n## ", 1)[0]
    faltando = {
        nome: onde
        for nome, onde in variaveis_lidas().items()
        if f"`{nome}`" not in secao
    }
    assert not faltando, (
        "Variáveis lidas pelo núcleo sem linha em 'Secrets e variáveis do núcleo' "
        f"do devagent/OPERACAO.md: {faltando}"
    )
