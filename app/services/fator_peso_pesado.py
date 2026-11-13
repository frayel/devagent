"""Apresentação do Fator Peso Pesado (specs 046 e 143).

A razão é `soma das contribuições das cinco / variação do índice × 100`, com
sinal. Positiva: as cinco andaram no mesmo sentido do índice. Negativa: no
sentido oposto. Módulo acima de 100: o restante do índice compensou. O teto de
±500% (spec 046) é visível: o card diz "limitado".
"""

from __future__ import annotations

from datetime import timedelta, timezone
from typing import Any

TETO = 500.0
MENOS = "−"  # sinal de menos tipográfico


def limitar(bruta: float) -> float:
    """Aplica o teto de ±500% da spec 046."""
    return max(-TETO, min(TETO, bruta))


def formatar_razao(valor: float) -> str:
    """Percentual com sinal e uma casa, no padrão brasileiro."""
    texto = f"{abs(valor):.1f}".replace(".", ",") + "%"
    if valor > 0:
        return "+" + texto
    if valor < 0:
        return MENOS + texto
    return texto


def frase(proporcao: float, limitado: bool) -> str:
    modulo = formatar_razao(abs(proporcao))
    if proporcao >= 0:
        texto = (
            "As 5 maiores ações andaram no mesmo sentido do Ibovespa, "
            f"somando {modulo} do tamanho do movimento."
        )
    else:
        texto = (
            "As 5 maiores ações andaram no sentido oposto ao do Ibovespa, "
            f"somando {modulo} do tamanho do movimento."
        )
    if abs(proporcao) > 100:
        texto += " O restante do índice compensou a diferença."
    if limitado:
        texto += f" Valor limitado ao teto de ±{TETO:.0f}%."
    return texto


def apresentar(dado: Any) -> dict[str, Any] | None:
    """Monta o dicionário usado pela página e pelo `/api/snapshot`."""
    if not dado:
        return None
    bruta = dado.proporcao_bruta
    if bruta is None:
        bruta = dado.proporcao
    proporcao = limitar(dado.proporcao)
    limitado = (not dado.mercado_lateral) and abs(bruta) > TETO
    view: dict[str, Any] = {
        "proporcao": 0.0 if dado.mercado_lateral else proporcao,
        "proporcao_bruta": 0.0 if dado.mercado_lateral else bruta,
        "limitado": limitado,
        "mercado_lateral": dado.mercado_lateral,
        "coletado_em": dado.timestamp.astimezone(
            timezone(timedelta(hours=-3))
        ).strftime("%d/%m/%Y %H:%M:%S BRT"),
        "fonte": dado.fonte,
    }
    if not dado.mercado_lateral:
        view["valor"] = formatar_razao(proporcao)
        view["sentido"] = "mesmo" if proporcao >= 0 else "oposto"
        view["frase"] = frase(proporcao, limitado)
    return view
