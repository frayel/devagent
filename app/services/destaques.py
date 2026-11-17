"""Faixa "Destaques agora", logo abaixo da manchete (spec 167).

Função pura: lê o que a rota `/` já montou (altas e baixas, confluência de
radares e o carimbo de altas e baixas) e devolve até três itens prontos para o
template. Não coleta nada e não recalcula nada.
"""

from __future__ import annotations

from typing import Any


def _hora(texto: str | None) -> str:
    """`HH:MM` de um carimbo `dd/mm/aaaa HH:MM[...] BRT`; vazio se não houver."""
    if not texto or len(texto) < 16:
        return ""
    return texto[11:16]


def _link(aba: str, data_historica: str | None) -> str:
    return f"?aba={aba}&data={data_historica}" if data_historica else f"?aba={aba}"


def _item_ativo(
    rotulo: str,
    vazio: str,
    lista: list[dict[str, Any]],
    positivo: bool,
    highlights: dict[str, Any],
    desatualizado: bool,
    data_historica: str | None,
) -> dict[str, Any]:
    primeiro = lista[0] if lista else None
    variacao = (primeiro or {}).get("change_percent")
    valido = isinstance(variacao, (int, float)) and (
        variacao > 0 if positivo else variacao < 0
    )
    if not primeiro or not valido:
        return {"tipo": "vazio", "rotulo": rotulo, "texto": vazio, "href": None}
    return {
        "tipo": "ativo",
        "rotulo": rotulo,
        "ticker": primeiro.get("ticker", ""),
        "variacao": primeiro.get("change_percent_formatted", ""),
        "sinal": 1 if positivo else -1,
        "hora": _hora(highlights.get("time")),
        "href": _link("rankings", data_historica),
        "title": f"Fonte: {highlights.get('fonte', '')} · {highlights.get('time', '')}",
        "desatualizado": desatualizado,
    }


def faixa(
    highlights: dict[str, Any] | None,
    confluencia: dict[str, Any] | None,
    carimbo_altas_baixas: dict[str, Any] | None,
    data_historica: str | None,
) -> list[dict[str, Any]]:
    """Até três itens: maior alta, maior baixa e a ação em mais radares."""
    itens: list[dict[str, Any]] = []
    desatualizado = bool((carimbo_altas_baixas or {}).get("desatualizado"))
    if highlights:
        itens.append(
            _item_ativo(
                "Maior alta",
                "nenhuma ação em alta",
                highlights.get("highs") or [],
                True,
                highlights,
                desatualizado,
                data_historica,
            )
        )
        itens.append(
            _item_ativo(
                "Maior baixa",
                "nenhuma ação em baixa",
                highlights.get("lows") or [],
                False,
                highlights,
                desatualizado,
                data_historica,
            )
        )

    acoes = (confluencia or {}).get("acoes") or []
    if acoes:
        primeira = acoes[0]
        n = len(primeira["radares"])
        empatadas = sum(1 for a in acoes[1:] if len(a["radares"]) == n)
        horario = (confluencia or {}).get("horario_texto", "")
        itens.append(
            {
                "tipo": "radares",
                "rotulo": "Em mais radares",
                "ticker": primeira["ticker"],
                "empate": f" e mais {empatadas}" if empatadas else "",
                "radares": f"{n} radares",
                "hora": _hora(horario),
                "href": _link("alertas", data_historica),
                "title": f"Fonte: os radares da aba Alertas · {horario}",
                "desatualizado": False,
            }
        )
    return itens
