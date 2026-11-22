"""Números e datas do Consultor no padrão brasileiro (spec 191).

Três funções puras, registradas como filtros do Jinja em `app/main.py`.
Nenhuma levanta exceção: valor ausente ou ilegível sai `-`.
"""

from __future__ import annotations

from app.consultor.armazenamento import ler_data, ler_preco_alvo
from app.services.carimbo import FUSO


def numero_br(x: float, casas: int = 2) -> str:
    """`1234.5` -> `1.234,50`: milhar com ponto, decimal com vírgula."""
    texto = f"{x:,.{casas}f}"
    return texto.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def reais(valor) -> str:
    """Preço em reais (`45.0`, `"52.5"`, `"R$ 1.234,50"`) -> `R$ 1.234,50`."""
    if valor is None or isinstance(valor, bool) or valor == "":
        return "-"
    x = ler_preco_alvo(valor)
    if x is None:
        return "-"
    return f"R$ {numero_br(x)}"


def percentual(fracao, casas: int = 1) -> str:
    """Fração (`0.123`) -> `+12,3%`, sempre com sinal."""
    if fracao is None or isinstance(fracao, bool):
        return "-"
    try:
        p = float(fracao) * 100
    except (TypeError, ValueError):
        return "-"
    return f"{p:+.{casas}f}".replace(".", ",") + "%"


def data_brasilia(momento) -> str:
    """Data ISO 8601 (UTC) -> `dd/mm/aaaa` no dia de Brasília."""
    dt = ler_data(momento)
    if dt is None:
        return "-"
    return dt.astimezone(FUSO).strftime("%d/%m/%Y")
