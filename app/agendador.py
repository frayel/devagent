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
import re
from datetime import datetime, time, timedelta, timezone
import importlib


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


def _mask_secrets(text: str) -> str:
    return re.sub(r"([?&]token=)[^&\s]+", r"\1***", text)


class _Memoria(logging.Handler):
    """Guarda os avisos e erros dos coletores da rodada, para /api/coleta."""

    def __init__(self) -> None:
        super().__init__(level=logging.WARNING)
        self.linhas: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.linhas.append(_mask_secrets(f"{record.name}: {record.getMessage()}"[:300]))


def coletar_tudo() -> None:
    """Roda os coletores em sequência. Falha de um não impede o outro."""
    memoria = _Memoria()
    raiz = logging.getLogger("app.collectors")
    raiz.addHandler(memoria)
    estado["ultimo_erro"] = None
    from typing import List

    estado_detalhes_manual: List[str] = []
    try:
        _coletar(estado_detalhes_manual)
    finally:
        raiz.removeHandler(memoria)
        linhas_finais = estado_detalhes_manual + memoria.linhas[-10:]
        estado["detalhes"] = (
            _mask_secrets("\n".join(linhas_finais)) if linhas_finais else None
        )
    estado["ultima_coleta"] = datetime.now(timezone.utc).isoformat()

    try:
        import app.banco

        app.banco.remover_snapshots_antigos(30)
    except Exception:
        pass


def _coletar(estado_detalhes_manual: list[str] | None = None) -> None:

    from app.collectors import mt5
    import time as std_time
    from app.database import save_coleta_vazia, save_coleta_tempo

    from app import calendario
    import app.banco

    janelas = {
        "clima_global": "pre_abertura",
        "consultor_opinioes": "continua",
        "consultor_historico": "semanal",
    }
    agora_brt = datetime.now(timezone.utc).astimezone(BRT)
    esta_aberto = calendario.mercado_aberto(datetime.now(timezone.utc))
    pregao_corr = calendario.pregao_corrente(datetime.now(timezone.utc))
    ult_fechado = calendario.ultimo_pregao_fechado(datetime.now(timezone.utc))
    eh_dia_pregao = calendario.e_pregao(agora_brt.date())
    passou_do_fechamento = agora_brt.time() > FIM_PREGAO

    estado_base = "ao_vivo"
    if esta_aberto:
        estado_base = "ao_vivo"
    elif eh_dia_pregao and passou_do_fechamento:
        if agora_brt.time() <= time(20, 0):
            estado_base = "final"
        else:
            estado_base = "incompleto"
    else:
        # Fim de semana ou pre abertura: os dados que serão gravados são partida a frio ou de ontem
        estado_base = "final"

    for nome in (
        "ibovespa",
        "highlights",
        "mare",
        "volume_alerts",
        "dolar_correlation",
        "sensibilidade_juros",
        "forca_relativa",
        "escudo_quedas",
        "coesao",
        "atrasadas_rally",
        "concentracao",
        "apetite_risco",
        "variacao_subita",
        "concentracao_setorial",
        "rotacao_capital",
        "faca_caindo",
        "compradores_fundo",
        "armadilha_abertura",
        "sobrevivencia_semanal",
        "radar_anomalia_fechamento",
        "volatilidade_silenciosa",
        "scanner_capitulacao",
        "radar_inflexao",
        "anomalia_peso",
        "radar_short_squeeze",
        "radar_congestionamento",
        "radar_liquidez_abertura",
        "esforco_resultado",
        "radar_divergencia_volume",
        "fator_peso_pesado",
        "falso_rompimento",
        "radar_absorcao_cruzada",
        "motores_indice",
        "clima_global",
        "relogio_volatilidade",
        "radar_anomalias_spread",
        "concentracao_ordens",
        "exaustao_tendencia",
        "exaustao_queda",
        "radar_exaustao_alta",
        "divergencia_ibov_dolar",
        "assimetria_risco_retorno",
        "consultor_historico",
        "consultor_opinioes",
    ):
        janela = janelas.get(nome, "pregao")
        deve_coletar = False
        eh_partida_a_frio = False
        data_ref_coleta = pregao_corr if esta_aberto else ult_fechado
        estado_coleta = estado_base

        if janela == "continua":
            deve_coletar = True
        elif janela == "semanal":
            if agora_brt.weekday() == 5:  # sábado
                deve_coletar = True
        elif janela == "pre_abertura":
            if eh_dia_pregao and (
                agora_brt.time() >= time(7, 0) and agora_brt.time() <= FIM_PREGAO
            ):
                deve_coletar = True
        else:  # pregao
            if esta_aberto:
                deve_coletar = True
            elif (
                eh_dia_pregao
                and passou_do_fechamento
                and agora_brt.time() <= time(20, 0)
            ):
                # Tentativa de fechamento
                last_snap = app.banco.ler_snapshot(nome, ult_fechado)
                if not last_snap or (
                    last_snap.get("estado_snapshot") != "final"
                    and last_snap.get("estado") != "final"
                ):
                    deve_coletar = True
                    estado_coleta = "final"
            else:
                # Partida a frio
                last_snap = app.banco.ler_snapshot(nome, ult_fechado)
                if not last_snap:
                    deve_coletar = True
                    eh_partida_a_frio = True
                    estado_coleta = "final"
                    data_ref_coleta = ult_fechado

        # Fallback de Partida a Frio para QUALQUER janela que não deva coletar normalmente
        if not deve_coletar:
            last_snap = app.banco.ler_snapshot(nome, ult_fechado)
            if not last_snap:
                deve_coletar = True
                eh_partida_a_frio = True
                estado_coleta = "final"
                data_ref_coleta = ult_fechado

        if not deve_coletar:
            continue

        coletor = importlib.import_module(f"app.collectors.{nome}")
        mt5.reiniciar_rastreio()
        try:
            if eh_partida_a_frio:
                logging.getLogger("app.collectors").warning(
                    f"Partida a frio para {nome}"
                )
                if estado_detalhes_manual is not None:
                    estado_detalhes_manual.append(f"{nome}: partida_a_frio")

            start_time = std_time.perf_counter()

            token_est = app.banco._estado_snapshot.set(estado_coleta)
            token_data = app.banco._data_referencia_snapshot.set(data_ref_coleta)
            try:
                ok = coletor.collect_and_save()
            finally:
                app.banco._estado_snapshot.reset(token_est)
                app.banco._data_referencia_snapshot.reset(token_data)
            if nome == "consultor_historico":
                from app.consultor import avaliador_historico

                # Avaliador não roda bloqueante no fluxo para não estourar o limite de tempo
                import threading

                threading.Thread(target=avaliador_historico.rodar_backtest).start()

            duracao = std_time.perf_counter() - start_time
            if nome == "consultor_historico":
                from app.consultor import avaliador_historico

                avaliador_historico.rodar_backtest()
            try:
                save_coleta_tempo(nome, duracao, datetime.now(timezone.utc))
            except Exception:
                logger.exception("Falha ao salvar tempo de coleta para %s", nome)
            if not ok:
                estado["ultimo_erro"] = f"{nome}: nenhuma fonte respondeu"
                try:
                    save_coleta_vazia(nome, datetime.now(timezone.utc))
                except Exception:
                    logger.exception("Falha ao salvar coleta vazia para %s", nome)
                if (
                    janela == "pregao"
                    and eh_dia_pregao
                    and passou_do_fechamento
                    and agora_brt.time() > time(20, 0)
                ):
                    last_snap = app.banco.ler_snapshot(nome, ult_fechado)
                    if (
                        last_snap
                        and last_snap.get("estado_snapshot")
                        not in ("incompleto", "final")
                        and last_snap.get("estado") not in ("incompleto", "final")
                    ):
                        app.banco.gravar_snapshot(
                            nome,
                            ult_fechado,
                            "incompleto",
                            last_snap.get("fonte", "banco"),
                            last_snap,
                        )
        except Exception as e:  # noqa: BLE001 - o laço não pode morrer
            logger.exception("Coleta de %s falhou", nome)
            estado["ultimo_erro"] = _mask_secrets(f"{nome}: {e}")


async def laco_de_coleta() -> None:
    while True:
        await asyncio.to_thread(coletar_tudo)
        espera = intervalo(datetime.now(timezone.utc))
        logger.info("Próxima coleta em %s", espera)
        await asyncio.sleep(espera.total_seconds())
