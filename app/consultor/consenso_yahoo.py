"""Consenso de analistas do Yahoo Finance na tela do Consultor (spec 159).

Só exibe: o consenso do Yahoo não entra na decisão nem no mínimo de 2 casas.
"""

from __future__ import annotations

from datetime import date

from app import calendario
from app.consultor.armazenamento import get_consenso_yahoo

GRUPOS_COM_CASAS = ("Comprar", "Vender", "Aguardar", "No radar")


def rotulo(media: float) -> str:
    """Escala do Yahoo: 1 = compra forte a 5 = venda forte."""
    if media <= 1.5:
        return "compra forte"
    if media <= 2.5:
        return "compra"
    if media <= 3.5:
        return "neutro"
    if media <= 4.5:
        return "venda"
    return "venda forte"


def _decimal(valor: float, casas: int) -> str:
    return f"{valor:.{casas}f}".replace(".", ",")


def frase(leitura: dict) -> str:
    """`Yahoo: compra (2,1) · 12 analistas · alvo médio R$ 15,40`."""
    media = leitura["recomendacao_media"]
    n = leitura["analistas"]
    partes = [
        f"Yahoo: {rotulo(media)} ({_decimal(media, 1)})",
        f"{n} {'analista' if n == 1 else 'analistas'}",
    ]
    if leitura.get("alvo_medio") is not None:
        partes.append(f"alvo médio R$ {_decimal(leitura['alvo_medio'], 2)}")
    return " · ".join(partes)


def datas_validas(data_referencia: date) -> list[str]:
    """A data de referência da página e o pregão anterior a ela."""
    return [
        calendario.pregao_anterior(data_referencia).isoformat(),
        data_referencia.isoformat(),
    ]


def para_api(leitura: dict | None) -> dict | None:
    if not leitura:
        return None
    return {
        "data": leitura["data"],
        "recomendacao_media": leitura["recomendacao_media"],
        "analistas": leitura["analistas"],
        "alvo_medio": leitura["alvo_medio"],
        "alvo_minimo": leitura["alvo_minimo"],
        "alvo_maximo": leitura["alvo_maximo"],
        "rotulo": rotulo(leitura["recomendacao_media"]),
        "frase": frase(leitura),
    }


def anexar(resultados: dict, data_referencia: date) -> None:
    """Põe `consenso_yahoo` (ou None) em cada ativo das tabelas com casas.

    Nunca levanta: sem tabela ou sem banco, o Consultor segue igual.
    """
    try:
        leituras = get_consenso_yahoo(datas_validas(data_referencia))
    except Exception:  # noqa: BLE001 - complemento opcional da tela
        leituras = {}
    for grupo, itens in (resultados or {}).items():
        for item in itens:
            if grupo in GRUPOS_COM_CASAS:
                item["consenso_yahoo"] = para_api(leituras.get(item.get("ticker")))
            else:
                item.setdefault("consenso_yahoo", None)
