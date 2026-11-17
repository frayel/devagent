"""Histórico longo da Maré: Ondas e Maré (spec 174a).

Uma vez por pregão completo, baixa dois anos da cesta e do Ibovespa (as mesmas
URLs do coletor `mare`, com `range=2y` na cesta) e grava o snapshot
`mare_historico` com:

- `leituras`: a leitura de cada um dos até 252 pregões completos mais
  recentes, pela mesma `_Calculadora` da Maré de hoje (sem fórmula nova);
- `heatmap_ondas` e `heatmap_mare`: as 10 ações de maior financeiro em cada
  janela (21 e 252 pregões);
- `ate`: o último pregão completo.

Quem decide quando roda é o agendador (janela `"diario"`); a conta dos níveis
fica em `app/services/mare.py` (`nivel`). Se o Yahoo falhar, nada é gravado e
a leitura continua no snapshot anterior.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Any

import httpx

from app import calendario
from app.collectors import mt5
from app.collectors.mare import buscar_cesta, buscar_ibov
from app.services import mare

logger = logging.getLogger(__name__)

URL_CESTA_2Y = (
    "https://{domain}.finance.yahoo.com/v8/finance/chart/{simbolo}?range=2y&interval=1d"
)


def calcular(
    cesta: dict[str, mare.SerieAcao],
    ibov: dict[date, float],
    ultimo_completo: date,
) -> dict[str, Any] | None:
    """Payload do snapshot, ou None quando não há nenhuma leitura."""
    calc = mare._Calculadora(cesta, ibov)
    dias = [d for d in (calc.sessoes or calc.dias_ibov) if d <= ultimo_completo]
    n_mare = mare.JANELAS_NIVEL["mare"]
    leituras = []
    for d in dias[-n_mare:]:
        leitura = calc.leitura(d, 1.0)
        if leitura.valor is None:
            continue
        c = leitura.componentes
        leituras.append(
            {
                "data": d.isoformat(),
                "valor": leitura.valor,
                "fluxo": c["fluxo"],
                "calma": c["calma"],
                "volume": c["volume"],
            }
        )
    if not leituras:
        return None

    sessoes = [d for d in calc.sessoes if d <= ultimo_completo]
    heatmaps: dict[str, list] = {}
    for nome, n in mare.JANELAS_NIVEL.items():
        janela = sessoes[-n:]
        anterior = sessoes[-n - 1] if len(sessoes) > n else None
        heatmaps[f"heatmap_{nome}"] = (
            mare.heatmap_janela(calc.acoes, janela, anterior)
            if anterior is not None
            else []
        )
    return {"leituras": leituras, **heatmaps, "ate": leituras[-1]["data"]}


def coletar(agora: datetime | None = None) -> dict[str, Any] | None:
    agora = agora or datetime.now(timezone.utc)
    ultimo = calendario.ultimo_pregao_fechado(agora)
    with httpx.Client(timeout=10.0) as client:
        cesta = buscar_cesta(client, URL_CESTA_2Y)
        ibov = buscar_ibov(client)
    payload = calcular(cesta, ibov, ultimo)
    if payload is None:
        logger.error(
            "Maré histórica: nenhuma leitura (%d ações, %d pregões do Ibovespa)",
            len(cesta),
            len(ibov),
        )
        return None
    payload["fonte"] = mt5.fonte_efetiva("yfinance")
    payload["coletado_em"] = agora.isoformat()
    return payload


def collect_and_save() -> bool:
    from app.banco import gravar_snapshot

    payload = coletar()
    if payload is None:
        return False
    gravar_snapshot(
        "mare_historico",
        date.fromisoformat(payload["ate"]),
        "final",
        payload["fonte"],
        payload,
    )
    logger.info(
        "Maré histórica gravada: %d leituras até %s",
        len(payload["leituras"]),
        payload["ate"],
    )
    return True


if __name__ == "__main__":
    collect_and_save()
