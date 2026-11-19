"""Memória da confluência dos radares: um registro por pregão fechado (spec 186).

Os snapshots dos radares vivem 30 datas (`remover_snapshots_antigos`), e a
confluência não se recalcula de preços: depende do que cada radar acusou no
dia. Uma vez por pregão fechado (janela `"diario"` do agendador), este coletor
guarda a confluência de cada pregão da janela de 30 que ainda não está no
snapshot `confluencia_historico`. Registro guardado nunca é recalculado.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Any

from app import calendario
from app.services import radares

logger = logging.getLogger(__name__)

JANELA_PREGOES = 30


def _pregoes(ultimo: date, n: int = JANELA_PREGOES) -> list[date]:
    datas = [ultimo]
    while len(datas) < n:
        datas.append(calendario.pregao_anterior(datas[-1]))
    return datas


def _registros_anteriores() -> list[dict[str, Any]]:
    from app.banco import ler_snapshot

    snapshot = ler_snapshot("confluencia_historico")
    registros = snapshot.get("registros") if isinstance(snapshot, dict) else None
    return list(registros) if isinstance(registros, list) else []


def collect_and_save() -> bool:
    import app.banco
    from app.main import _payloads_radares  # import tardio: evita ciclo com app.main

    agora = datetime.now(timezone.utc)
    ultimo = calendario.ultimo_pregao_fechado(agora)
    registros = _registros_anteriores()
    guardadas = {r.get("data") for r in registros}
    novos: list[dict[str, Any]] = []
    for d in _pregoes(ultimo):
        if d.isoformat() in guardadas:
            continue
        try:
            with app.banco.lendo_pregao(d):
                payloads = _payloads_radares()
            registro = radares.registro_do_pregao(payloads, d)
        except Exception:  # noqa: BLE001 - um pregão ruim não derruba os outros
            logger.exception("Confluência de %s não lida; fica para amanhã", d)
            continue
        if registro is not None:
            novos.append(registro)

    todos = radares.acumular(registros, novos)
    if not todos:
        return False
    payload = {
        "registros": todos,
        "de": todos[0]["data"],
        "ate": todos[-1]["data"],
        "fonte": "composto",
        "coletado_em": agora.isoformat(),
    }
    app.banco.gravar_snapshot(
        "confluencia_historico", ultimo, "final", "composto", payload
    )
    logger.info(
        "Confluência guardada: %d pregões (%d novos) até %s",
        len(todos),
        len(novos),
        payload["ate"],
    )
    return True


if __name__ == "__main__":
    collect_and_save()
