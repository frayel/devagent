"""Coleta periódica dentro do próprio web service.

Por que aqui e não num Cron Job do Render: no plano gratuito o disco é
efêmero e não é compartilhado entre serviços, então um cron job gravaria num
banco que o site não enxerga (ADR 004). O web service coleta ao subir e
depois em intervalos: a cada 15 minutos durante o pregão, a cada 2 horas fora
dele. Quando o Render hiberna o serviço, a coleta para; ao acordar, ela roda
de novo antes de qualquer outra coisa.

Desligue com COLETA_AUTOMATICA=0 (os testes fazem isso).
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, time, timedelta, timezone


logger = logging.getLogger(__name__)

BRT = timezone(timedelta(hours=-3))
INICIO_PREGAO = time(9, 55)
FIM_PREGAO = time(18, 15)
NO_PREGAO = timedelta(minutes=15)
FORA_DO_PREGAO = timedelta(hours=2)

# Estado da última rodada, exposto em /api/coleta para diagnóstico.
estado: dict[str, str | None] = {
    "ultima_coleta": None,
    "ultimo_erro": None,
    "detalhes": None,
}


def coleta_ligada() -> bool:
    if "PYTEST_CURRENT_TEST" in os.environ:
        return False
    return os.environ.get("COLETA_AUTOMATICA", "1") not in {"0", "false", "False"}


def intervalo(agora: datetime) -> timedelta:
    """Quanto esperar até a próxima coleta."""
    local = agora.astimezone(BRT)
    if local.weekday() < 5 and INICIO_PREGAO <= local.time() <= FIM_PREGAO:
        return NO_PREGAO
    return FORA_DO_PREGAO


class _Memoria(logging.Handler):
    """Guarda os avisos e erros dos coletores da rodada, para /api/coleta."""

    def __init__(self) -> None:
        super().__init__(level=logging.WARNING)
        self.linhas: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.linhas.append(f"{record.name}: {record.getMessage()}"[:300])


def coletar_tudo() -> None:
    """Roda os coletores em sequência. Falha de um não impede o outro."""
    memoria = _Memoria()
    raiz = logging.getLogger("app.collectors")
    raiz.addHandler(memoria)
    estado["ultimo_erro"] = None
    try:
        _coletar()
    finally:
        raiz.removeHandler(memoria)
        estado["detalhes"] = "\n".join(memoria.linhas[-10:]) or None
    estado["ultima_coleta"] = datetime.now(timezone.utc).isoformat()


def _coletar() -> None:

    import importlib

    for nome in (
        "ibovespa",
        "highlights",
        "volume_alerts",
        "dolar_correlation",
        "forca_relativa",
        "escudo_quedas",
        "coesao",
        "atrasadas_rally",
    ):
        coletor = importlib.import_module(f"app.collectors.{nome}")
        try:
            ok = coletor.collect_and_save()
            if not ok:
                estado["ultimo_erro"] = f"{nome}: nenhuma fonte respondeu"
        except Exception as e:  # noqa: BLE001 - o laço não pode morrer
            logger.exception("Coleta de %s falhou", nome)
            estado["ultimo_erro"] = f"{nome}: {e}"


async def laco_de_coleta() -> None:
    while True:
        await asyncio.to_thread(coletar_tudo)
        espera = intervalo(datetime.now(timezone.utc))
        logger.info("Próxima coleta em %s", espera)
        await asyncio.sleep(espera.total_seconds())
