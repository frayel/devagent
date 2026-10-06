"""Cálculo do gauge (docs/DESIGN.md, seção 5.2; spec 026).

A macro `gauge` de `componentes.html` só posiciona o que sai daqui: a fração
do arco, o deslocamento do modo divergente, a cor, a faixa atual e o texto do
número no padrão brasileiro. Assim cada regra tem teste de unidade e o
template não faz conta.
"""

from __future__ import annotations

import re
from typing import Any

# Classe de cor de cada faixa, da pior para a melhor (DESIGN.md, seção 5.2).
CORES_DAS_FAIXAS = {
    1: [3],
    2: [1, 5],
    3: [1, 3, 5],
    4: [1, 2, 4, 5],
    5: [1, 2, 3, 4, 5],
}
VAO_ENTRE_FAIXAS = 1.0


def numero_br(valor: float, formato: str) -> str:
    """Formata com o `formato` do Python e troca o separador decimal."""

    def troca(campo: re.Match[str]) -> str:
        numero = campo.group(0).format(valor)
        return numero.replace(".", "\x00").replace(",", ".").replace("\x00", ",")

    # Só o campo numérico troca de separador; a unidade ("p.p.") fica como está.
    return re.sub(r"\{[^}]*\}", troca, formato)


def gauge_pct(valor: float, minimo: float = 0, maximo: float = 100) -> float:
    """Posição do valor no arco, de 0 a 100, cortada nos limites."""
    if maximo == minimo:
        return 0.0
    pct = (float(valor) - minimo) / (maximo - minimo) * 100
    return max(0.0, min(100.0, pct))


def _arredonda(x: float) -> str:
    """Número para atributo SVG: até 2 casas, sem zeros à direita, sem "-0"."""
    return f"{round(x, 2) + 0.0:g}"


def dados(
    valor: float | None,
    rotulo: str,
    minimo: float = 0,
    maximo: float = 100,
    formato: str = "{:.0f}",
    faixas: list[str] | None = None,
    divergente: bool = False,
    resumo: str = "",
    cor: str | None = None,
) -> dict[str, Any] | None:
    """Tudo que a macro precisa para desenhar. None quando não há valor."""
    if valor is None:
        return None
    valor = float(valor)
    pct = gauge_pct(valor, minimo, maximo)
    texto = numero_br(valor, formato)
    fora = valor > maximo or valor < minimo

    d: dict[str, Any] = {
        "pct": _arredonda(pct),
        "texto": texto,
        "rotulo": rotulo,
        "divergente": divergente,
        "fora": fora,
        "minimo_texto": numero_br(minimo, formato),
        "maximo_texto": numero_br(maximo, formato),
        "faixas": [],
        "agulha": None,
    }

    if divergente:
        d["dasharray"] = _arredonda(abs(pct - 50))
        d["dashoffset"] = _arredonda(-min(pct, 50))
        d["cor"] = cor or ("alta" if valor > 0 else "baixa" if valor < 0 else "neutra")
    else:
        d["dasharray"] = d["pct"]
        d["dashoffset"] = None
        d["cor"] = cor or ("alta" if pct >= 50 else "baixa")

    if faixas:
        n = len(faixas)
        if n not in CORES_DAS_FAIXAS:
            raise ValueError("o gauge aceita de 1 a 5 faixas")
        largura = 100 / n
        cores = CORES_DAS_FAIXAS[n]
        atual = min(int(pct // largura), n - 1)
        d["faixas"] = [
            {
                "indice": i + 1,
                "cor": f"g-cor-{cores[i]}",
                "dasharray": _arredonda(largura - VAO_ENTRE_FAIXAS),
                "dashoffset": _arredonda(-(i * largura + VAO_ENTRE_FAIXAS / 2)),
            }
            for i in range(n)
        ]
        d["faixa"] = faixas[atual]
        d["cor"] = f"g-cor-{cores[atual]}"
        d["agulha"] = _arredonda(pct * 1.8 - 90)
        d["rotulo"] = faixas[atual]

    partes = [f"{resumo or d['rotulo']}: {texto}"]
    if resumo and d["rotulo"]:
        partes.append(d["rotulo"])
    if fora:
        partes.append("fora da escala")
    d["aria"] = ", ".join(partes)
    return d
