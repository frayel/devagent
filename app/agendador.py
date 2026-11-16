# Verificação de specs concluída sem achados recém-implementados.
"""Coleta periódica dentro do próprio web service.

Por que aqui e não num Cron Job do Render: no plano gratuito o disco é
efêmero e não é compartilhado entre serviços, então um cron job gravaria num
banco que o site não enxerga (ADR 004). O web service coleta ao subir e
depois em intervalos: a cada 15 minutos durante o pregão, a cada 2 horas fora
dele, contados do começo de uma rodada ao da próxima (spec 163). Quando o Render hiberna o serviço, a coleta para; ao acordar, ela roda
de novo antes de qualquer outra coisa.

Desligue com COLETA_AUTOMATICA=0 (os testes fazem isso).
"""

from __future__ import annotations

import asyncio
import logging
import threading
import os
import re
import time as std_time
from datetime import date, datetime, time, timedelta, timezone
import importlib


logger = logging.getLogger(__name__)

BRT = timezone(timedelta(hours=-3))
INICIO_PREGAO = time(9, 55)
FIM_PREGAO = time(18, 15)
NO_PREGAO = timedelta(minutes=15)
FORA_DO_PREGAO = timedelta(hours=2)
# Pausa entre o fim de uma rodada e o começo da próxima, mesmo quando a rodada
# passa do intervalo: as rodadas nunca se sobrepõem nem começam coladas (spec 163).
PAUSA_MINIMA = timedelta(seconds=60)

# Estado da última rodada, exposto em /api/coleta para diagnóstico.

_backtest_rodando = False
_backtest_lock = threading.Lock()

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
    import app.calendario

    if app.calendario.e_pregao(local.date()):
        if INICIO_PREGAO <= local.time() <= FIM_PREGAO:
            return NO_PREGAO
        elif FIM_PREGAO < local.time() <= time(20, 0):
            return timedelta(minutes=30)
    return FORA_DO_PREGAO


# Variáveis cujo valor nunca aparece em log nem em /api/coleta (spec 141).
SEGREDOS_DO_AMBIENTE = (
    "MT5_API_KEY",
    "DATABASE_URL",
    "GITHUB_TOKEN",
    "GEMINI_API_KEY",
    "JULES_API_KEY",
    "RENDER_API_KEY",
    "CONSULTOR_SENHA",
)


def _mask_secrets(text: str) -> str:
    text = re.sub(r"([?&](?:token|key|api_key)=)[^&\s]+", r"\1***", text)
    for var in SEGREDOS_DO_AMBIENTE:
        valor = os.environ.get(var)
        if valor and len(valor) >= 4:
            text = text.replace(valor, "***")
    return text


def _avisar_falha(mensagem: str, nome: str, e: BaseException) -> None:
    """Aviso de coletor que falhou: fonte, tipo da exceção e texto mascarado.

    Sem traceback: a mensagem de uma exceção HTTP pode trazer a chave da URL.
    """
    logger.warning(
        "%s %s: %s: %s",
        mensagem,
        nome,
        type(e).__name__,
        _mask_secrets(str(e))[:300],
    )


class _Memoria(logging.Handler):
    """Guarda os avisos e erros dos coletores da rodada, para /api/coleta."""

    def __init__(self) -> None:
        super().__init__(level=logging.WARNING)
        self.linhas: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.linhas.append(_mask_secrets(f"{record.name}: {record.getMessage()}"[:300]))


_ultimo_erro_sistemico = False


def _eh_erro_sistemico(e: Exception | str) -> bool:
    """Identifica falhas de infraestrutura/sistêmicas (banco, rede, disjuntor)."""
    try:
        from app.banco import DBInacessivelError

        if isinstance(e, DBInacessivelError):
            return True
    except ImportError:
        pass

    nome_classe = type(e).__name__ if isinstance(e, Exception) else ""
    texto = str(e).lower()
    return (
        "disjuntor" in texto
        or "dbinacessivel" in texto
        or "db_inacessivel" in texto
        or "timeout" in texto
        or "connection" in texto
        or "conexao" in texto
        or "operationalerror" in nome_classe.lower()
        or isinstance(e, (ConnectionError, OSError))
    )


def _formatar_erro(nome: str, erro: Exception | str, prefixo: str | None = None) -> str:
    if isinstance(erro, Exception):
        detalhe = str(erro) or type(erro).__name__
    else:
        detalhe = str(erro)
    if prefixo:
        return f"{nome}: {prefixo}: {detalhe}"
    return f"{nome}: {detalhe}"


def _registrar_erro(msg: str, eh_sistemico: bool = False) -> None:
    """Registra erro preservando a falha original ou sistêmica mais crítica da rodada."""
    global _ultimo_erro_sistemico
    msg_mascarada = _mask_secrets(msg)
    if estado["ultimo_erro"] is None:
        estado["ultimo_erro"] = msg_mascarada
        _ultimo_erro_sistemico = eh_sistemico
    elif eh_sistemico and not _ultimo_erro_sistemico:
        estado["ultimo_erro"] = msg_mascarada
        _ultimo_erro_sistemico = True


def coletar_tudo() -> None:
    """Roda os coletores em sequência. Falha de um não impede o outro."""
    global _ultimo_erro_sistemico
    _ultimo_erro_sistemico = False
    memoria = _Memoria()
    raiz = logging.getLogger("app.collectors")
    raiz.addHandler(memoria)
    estado["ultimo_erro"] = None
    from typing import List

    estado_detalhes_manual: List[str] = []
    try:
        _coletar(estado_detalhes_manual)
    except Exception as e:
        logger.exception("Falha fatal no loop de coleta")
        estado["ultimo_erro"] = _mask_secrets(f"Falha fatal: {e}")
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


def _radares_escondidos(pregao: date | None) -> list[str] | None:
    """Radares que a aba Alertas esconde no pregão, numa consulta só (spec 166).

    Falha na leitura vira `None`: a rodada não conta para os radares e o resto
    da instrumentação é gravado como sempre.
    """
    import app.banco
    from app.services.radares import RADARES, SNAPSHOT_DO_RADAR, escondidos

    try:
        with app.banco.req_snapshot_cache_ctx():
            payloads = {
                c: app.banco.ler_snapshot(SNAPSHOT_DO_RADAR.get(c, c), pregao)
                for c, _n, _f in RADARES
            }
        return escondidos(payloads)
    except Exception:
        logger.exception("Falha ao ler os radares escondidos da rodada")
        return None


def _coletar(estado_detalhes_manual: list[str] | None = None) -> None:
    import time as std_time

    # Relógio da rodada inteira (spec 162): começa antes das leituras do calendário.
    inicio_rodada = datetime.now(timezone.utc)
    t0_rodada = std_time.perf_counter()

    from app.collectors import mt5
    from app.database import gravar_instrumentacao_rodada

    from app import calendario
    import app.banco

    janelas = {
        "clima_global": "pre_abertura",
        "consultor_historico": "semanal",
        "consultor_fechamento": "fechamento",
        "consultor_yahoo": "fechamento",
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

    # Instrumentação acumulada em memória e gravada uma vez no fim da rodada (spec 152).
    tempos: dict[str, float] = {}
    vazias: list[str] = []
    try:
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
            "correlacao_di",
            "assimetria_risco_retorno",
            "consultor_historico",
            "consultor_fechamento",
            "consultor_yahoo",
        ):
            try:
                janela = janelas.get(nome, "pregao")
                deve_coletar = False
                eh_partida_a_frio = False
                data_ref_coleta = pregao_corr if esta_aberto else ult_fechado
                estado_coleta = estado_base

                if janela == "semanal":
                    if agora_brt.weekday() == 5:  # sábado
                        deve_coletar = True
                elif janela == "pre_abertura":
                    if eh_dia_pregao and (
                        agora_brt.time() >= time(7, 0)
                        and agora_brt.time() <= FIM_PREGAO
                    ):
                        deve_coletar = True
                elif janela == "fechamento":
                    if (
                        eh_dia_pregao
                        and passou_do_fechamento
                        and agora_brt.time() <= time(20, 0)
                    ):
                        deve_coletar = True
                        estado_coleta = "final"
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
                    elif (
                        eh_dia_pregao
                        and passou_do_fechamento
                        and agora_brt.time() > time(20, 0)
                    ) or (agora_brt.date() > ult_fechado):
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
                            if estado_detalhes_manual is not None:
                                estado_detalhes_manual.append(f"{nome}: incompleto")
                        elif not last_snap:
                            # Partida a frio
                            deve_coletar = True
                            eh_partida_a_frio = True
                            estado_coleta = "final"
                            data_ref_coleta = ult_fechado
                    else:
                        # Partida a frio fallback
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
                    token_data = app.banco._data_referencia_snapshot.set(
                        data_ref_coleta
                    )
                    try:
                        ok = coletor.collect_and_save()
                    finally:
                        app.banco._estado_snapshot.reset(token_est)
                        app.banco._data_referencia_snapshot.reset(token_data)
                    if nome == "consultor_historico":
                        from app.consultor import avaliador_historico

                        global _backtest_rodando
                        with _backtest_lock:
                            ja_rodando = _backtest_rodando
                            if not ja_rodando:
                                _backtest_rodando = True

                        if ja_rodando:
                            if estado_detalhes_manual is not None:
                                estado_detalhes_manual.append(
                                    "consultor_historico: backtest anterior ainda em curso"
                                )
                        else:

                            def _wrapper_backtest():
                                global _backtest_rodando
                                try:
                                    avaliador_historico.rodar_backtest()
                                finally:
                                    with _backtest_lock:
                                        _backtest_rodando = False

                            t = threading.Thread(target=_wrapper_backtest, daemon=True)
                            t.start()

                    duracao = std_time.perf_counter() - start_time
                    tempos[nome] = duracao
                    if not ok:
                        _registrar_erro(
                            f"{nome}: nenhuma fonte respondeu", eh_sistemico=False
                        )
                        vazias.append(nome)
                except Exception as e:  # noqa: BLE001 - o laço não pode morrer
                    _avisar_falha("Coleta falhou:", nome, e)
                    msg = _formatar_erro(nome, e)
                    if estado_detalhes_manual is not None:
                        estado_detalhes_manual.append(_mask_secrets(msg))
                    _registrar_erro(msg, eh_sistemico=_eh_erro_sistemico(e))
            except Exception as e:
                _avisar_falha("Falha ao inicializar ou coletar:", nome, e)
                msg = _formatar_erro(nome, e, prefixo="erro fatal")
                if estado_detalhes_manual is not None:
                    estado_detalhes_manual.append(_mask_secrets(msg))
                _registrar_erro(msg, eh_sistemico=_eh_erro_sistemico(e))
    finally:
        radares_escondidos = _radares_escondidos(pregao_corr) if esta_aberto else None
        try:
            duracao_parede = std_time.perf_counter() - t0_rodada
            gravar_instrumentacao_rodada(
                tempos,
                vazias,
                datetime.now(timezone.utc),
                durante_pregao=esta_aberto,
                inicio=inicio_rodada,
                duracao_parede=duracao_parede,
                radares_escondidos=radares_escondidos,
            )
        except Exception:
            logger.exception("Falha ao gravar a instrumentação da rodada")


def proxima_espera(intervalo_atual: timedelta, duracao: timedelta) -> timedelta:
    """Espera depois da rodada para que a próxima comece um intervalo depois
    do começo desta, nunca menos que PAUSA_MINIMA (spec 163)."""
    return max(intervalo_atual - duracao, PAUSA_MINIMA)


def _relogio() -> float:
    """Relógio monotônico da duração da rodada; existe para o teste trocá-lo."""
    return std_time.monotonic()


async def laco_de_coleta() -> None:
    while True:
        t0 = _relogio()
        await asyncio.to_thread(coletar_tudo)
        duracao = timedelta(seconds=_relogio() - t0)
        # O intervalo é o do fim da rodada: depois das 18h15 já vale o de 30 min.
        espera = proxima_espera(intervalo(datetime.now(timezone.utc)), duracao)
        logger.info("Rodada levou %s; próxima coleta em %s", duracao, espera)
        await asyncio.sleep(espera.total_seconds())


def rodar_opinioes() -> None:
    """Uma volta do laço das opiniões (spec 164), fora da rodada de mercado.

    Não toca em `estado`, `tempos` nem na instrumentação: esses são da rodada
    de mercado. As falhas de cada fonte seguem pelo `registro_fontes`."""
    from app.collectors import consultor_opinioes

    try:
        if not consultor_opinioes.collect_and_save():
            logger.warning("consultor_opinioes: nenhuma fonte respondeu")
    except Exception as e:  # noqa: BLE001 - o laço não pode morrer
        _avisar_falha("Coleta falhou:", "consultor_opinioes", e)


async def laco_das_opinioes() -> None:
    """Lê as opiniões no mesmo ritmo da rodada de mercado, ao lado dela (spec 164)."""
    while True:
        t0 = _relogio()
        await asyncio.to_thread(rodar_opinioes)
        duracao = timedelta(seconds=_relogio() - t0)
        espera = proxima_espera(intervalo(datetime.now(timezone.utc)), duracao)
        logger.info("Opiniões levaram %s; próxima leitura em %s", duracao, espera)
        await asyncio.sleep(espera.total_seconds())
