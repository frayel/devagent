from typing import Any
from app.banco import get_backend_type


import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi.responses import JSONResponse
from app.consultor.calculador import calcular_consultor
from app.consultor.universo import (
    composicao_esta_desatualizada,
    FONTE_URL,
    CARTEIRA_IBOVESPA,
    COMPOSICAO_VIGENTE_ATE,
)
import secrets
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import os
from fastapi import FastAPI, Request, Query
from app import calendario
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates

from app import gauge
from fastapi.staticfiles import StaticFiles

import json
from datetime import datetime, timezone, timedelta
from datetime import timezone as dt_timezone
from app.services.ibovespa import get_ibovespa_view_data
from app.services.manchete import gerar_manchete
from app.database import get_latest_highlights_data, get_latest_apetite_risco_data
from app.services.highlights import get_highlights_view_data
from app.services.volume_alerts import get_volume_alerts_view_data
from app.services.dolar_correlation import get_dolar_correlation_view_data
from app.services.sensibilidade_juros import get_sensibilidade_juros_view_data
from app.services.forca_relativa import get_forca_relativa_view_data
from app.services.escudo_quedas import get_escudo_quedas_view_data
from app.services.coesao import get_coesao_view_data
from app.services.atrasadas_rally import get_atrasadas_rally_view_data
from app.services.concentracao import (
    get_concentracao_view_data,
    get_concentracao_vendedora_view_data,
)
from app.services.apetite_risco import get_apetite_risco_view_data
from app.services.variacao_subita import get_variacao_subita_view_data
from app.services.radar_anomalia_fechamento import get_radar_anomalia_fechamento_view
from app.services.rotacao_capital import get_rotacao_capital_view
from app.services.faca_caindo import get_faca_caindo_view
from app.services.compradores_fundo import get_compradores_fundo_view
from app.services.armadilha_abertura import get_armadilha_abertura_view
from app.services.sobrevivencia_semanal import get_sobrevivencia_semanal_view
from app.services.volatilidade_silenciosa import get_volatilidade_silenciosa_view
from app.services.correlacao_di import get_correlacao_di_view_data
from app.services import scanner_capitulacao
from app.services import mare as mare_servico
from app.database import (
    get_divergencia_ibov_dolar,
    get_latest_assimetria_risco_retorno_data,
    get_latest_motores_indice_data,
    get_latest_clima_global_data,
    get_latest_relogio_volatilidade_data,
    get_latest_concentracao_setorial_data,
    get_latest_ibovespa_data,
    get_latest_volume_alerts_data,
    get_latest_dolar_correlation_data,
    get_latest_sensibilidade_juros_data,
    get_latest_forca_relativa_data,
    get_latest_escudo_quedas_data,
    get_latest_coesao_data,
    get_latest_atrasadas_rally_data,
    get_latest_concentracao_data,
    get_latest_concentracao_vendedora_data,
    get_latest_variacao_subita_data,
    get_latest_rotacao_capital_data,
    get_latest_compradores_fundo_data,
    get_latest_armadilha_abertura_data,
    get_latest_sobrevivencia_semanal_data,
    get_latest_mare_data,
    get_latest_radar_anomalias_spread_data,
    get_latest_concentracao_ordens_data,
    get_latest_exaustao_tendencia_data,
    get_latest_exaustao_queda_data,
    get_latest_exaustao_alta_data,
)
from app import agendador
from app.services import sistema as sistema_servico

# Quando esta instância subiu: o Render reinicia o processo a cada deploy e a
# cada vez que acorda o serviço hibernado (página /sistema, spec 082).
INICIO = datetime.now(timezone.utc)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    tarefas = []
    if agendador.coleta_ligada():
        tarefas.append(asyncio.create_task(agendador.laco_de_coleta()))
    from app.collectors import sistema as monitor_sistema

    if monitor_sistema.monitor_ligado():
        tarefas.append(asyncio.create_task(monitor_sistema.laco_do_monitor()))
    from app.services import validador_gemini

    tarefas.append(asyncio.create_task(validador_gemini.laco_da_validacao()))
    yield
    for tarefa in tarefas:
        tarefa.cancel()


logger = logging.getLogger(__name__)

app = FastAPI(lifespan=lifespan)
templates = Jinja2Templates(directory="app/templates")
# Cálculo dos gauges (spec 026): a macro só posiciona o que sai de app/gauge.py.
templates.env.globals["gauge_dados"] = gauge.dados
templates.env.filters["gauge_pct"] = gauge.gauge_pct
templates.env.globals["render_no_db"] = (
    os.environ.get("RENDER") and get_backend_type() != "postgres"
)


app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > 1_000_000:  # 1MB limit
        return PlainTextResponse("Payload Too Large", status_code=413)
    return await call_next(request)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    response.headers["Strict-Transport-Security"] = (
        "max-age=31536000; includeSubDomains"
    )
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' https://unpkg.com https://cdn.plot.ly; "
        "style-src 'self' 'sha256-47DEQpj8HBSa+/TImW+5JCeuQeRkm5NMpJWZG3hSuFU=' 'sha256-pgn1TCGZX6O77zDvy0oTODMOxemn0oj0LeCnQTRj7Kg='; "
        "img-src 'self' data:; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'none'"
    )

    return response


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/api/coleta")
def coleta():
    """Diagnóstico da coleta automática (última rodada e último erro)."""
    from app.agendador import estado

    return estado


def _get_seletor_context(
    target_data: str | None, agora: datetime, mercado_aberto: bool, pregao_corr
):
    datas_disponiveis = obter_pregoes_disponiveis(agora, mercado_aberto, pregao_corr)
    data_ref = (
        calendario.ultimo_pregao_fechado(agora) if not mercado_aberto else pregao_corr
    )

    is_historical = False
    estado_mercado = "aberto" if mercado_aberto else "fechado"
    data_invalida = False

    if target_data:
        if target_data in datas_disponiveis:
            try:
                data_ref = datetime.strptime(target_data, "%Y-%m-%d").date()
                is_historical = True
                estado_mercado = "fechado"
            except ValueError:
                pass
        else:
            data_invalida = True

    DIAS = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
    datas_seletor = []
    for i, d_str in enumerate(datas_disponiveis):
        if i == 0 and not is_historical and estado_mercado == "aberto":
            rotulo = "Hoje"
        elif i == 0 and not is_historical:
            rotulo = "Último fechamento"
        else:
            try:
                dt = datetime.strptime(d_str, "%Y-%m-%d").date()
                rotulo = f"{dt.strftime('%d/%m')} {DIAS[dt.weekday()]}"
            except Exception:
                rotulo = d_str
        datas_seletor.append((d_str, rotulo))

    return {
        "datas_disponiveis": datas_disponiveis,
        "datas_seletor": datas_seletor,
        "data_referencia": data_ref,
        "is_historical": is_historical,
        "estado_mercado": estado_mercado,
        "data_invalida": data_invalida,
    }


def obter_pregoes_disponiveis(agora, mercado_aberto, pregao_corr):
    from app.banco import listar_datas, PREGOES_NO_SELETOR

    datas_banco = listar_datas("ibovespa", 30)
    pregoes = []

    if mercado_aberto:
        s_corr = str(pregao_corr)
        pregoes.append(s_corr)

    for d in datas_banco:
        if d not in pregoes:
            pregoes.append(d)
        if len(pregoes) >= PREGOES_NO_SELETOR + 1:
            break

    return pregoes[: PREGOES_NO_SELETOR + 1]

    res = {"ligada": agendador.coleta_ligada(), **agendador.estado}
    backend = get_backend_type()
    if os.environ.get("RENDER") and backend != "postgres":
        res["aviso"] = "Banco persistente não configurado: dados se perdem ao reiniciar"
    res["banco"] = backend
    return res


HORAS_VAZIOS = 3


def estado_do_sistema() -> dict:
    """Verificações da página /sistema (spec 082). Só lê: não chama fonte externa."""
    from app import database
    from app import banco as banco_module
    from app.collectors import mt5 as mt5_coletor
    from app.collectors import registro_fontes
    from app.services import gemini_modelo
    from app.collectors import sistema as monitor_sistema

    agora = datetime.now(timezone.utc)
    try:
        vazios = database.get_coletas_vazias_desde(
            agora - timedelta(hours=HORAS_VAZIOS)
        )
        rodadas = database.get_rodadas_coleta_desde(
            agora - timedelta(hours=HORAS_VAZIOS)
        )
        tempos = database.get_tempos_coleta_desde(agora - timedelta(hours=24))
    except Exception:  # tabelas ainda não criadas: a verificação do banco acusa
        vazios, rodadas, tempos = {}, {}, {}
    return sistema_servico.montar(
        agora=agora,
        inicio=INICIO,
        remoto=dict(monitor_sistema.retrato),
        sha_local=monitor_sistema.commit_em_producao(),
        banco=banco_module.diagnostico(),
        coleta_ligada=agendador.coleta_ligada(),
        estado_coleta=dict(agendador.estado),
        intervalo_coleta=agendador.intervalo(agora),
        vazios=vazios,
        horas_vazios=HORAS_VAZIOS,
        rodadas=rodadas,
        tempos=tempos,
        historico_pregoes=banco_module.listar_datas("ibovespa", 30),
        fontes=registro_fontes.fontes(),
        pausa_mt5=mt5_coletor.pausa(),
        prontas=sistema_servico.specs_prontas(),
        monitor_ligado=monitor_sistema.monitor_ligado(),
        modelo_gemini=gemini_modelo.descricao(),
    )


@app.get("/api/sistema")
def api_sistema(request: Request):
    exigir_senha(request)
    return estado_do_sistema()


@app.get("/sistema", response_class=HTMLResponse)
def pagina_sistema(request: Request):
    exigir_senha(request)
    estado = estado_do_sistema()
    agora = datetime.now(timezone.utc)
    mercado_aberto = calendario.mercado_aberto(agora)
    pregao_corr = calendario.pregao_corrente(agora)
    ctx = _get_seletor_context(None, agora, mercado_aberto, pregao_corr)

    return templates.TemplateResponse(
        request=request,
        name="sistema.html",
        context={
            "data": None,
            "sistema": estado,
            "gerado_txt": sistema_servico.hora_brt(estado["gerado_em"]),
            "remoto_txt": sistema_servico.hora_brt(estado["remoto_em"]),
            "datas_seletor": ctx["datas_seletor"],
            "data_referencia": ctx["data_referencia"],
            "is_historical": ctx["is_historical"],
            "data_invalida": ctx["data_invalida"],
        },
    )


security = HTTPBasic()


def exigir_senha(request: Request) -> None:
    """HTTP Basic com CONSULTOR_SENHA (usuário `consultor`); sem a variável, libera.

    Protege as páginas que podem ficar privadas se o site for publicado: o
    Consultor (ADR 005) e a página de sistema (spec 082).
    """
    senha_correta = os.environ.get("CONSULTOR_SENHA")
    if not senha_correta:
        return
    negado = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais requeridas",
        headers={"WWW-Authenticate": "Basic"},
    )
    esquema, _, param = (request.headers.get("Authorization") or "").partition(" ")
    if esquema.lower() != "basic":
        raise negado
    try:
        import base64

        usuario, _, senha = base64.b64decode(param).decode("utf-8").partition(":")
    except Exception:
        raise negado
    usuario_ok = secrets.compare_digest(usuario, "consultor")
    senha_ok = secrets.compare_digest(senha, senha_correta)
    if not (usuario_ok and senha_ok):
        raise negado


def verificar_credenciais(credentials: HTTPBasicCredentials = Depends(security)):
    senha_correta = os.environ.get("CONSULTOR_SENHA")
    if not senha_correta:
        return True

    is_user_ok = secrets.compare_digest(credentials.username, "consultor")
    is_pass_ok = secrets.compare_digest(credentials.password, senha_correta)

    if not (is_user_ok and is_pass_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais incorretas",
            headers={"WWW-Authenticate": "Basic"},
        )
    return True


@app.get("/consultor")
def pagina_consultor(
    request: Request,
    data: str | None = Query(default=None, alias="data"),
    data_str: str | None = None,
):
    exigir_senha(request)

    target_data = data or data_str
    agora = datetime.now(timezone.utc)
    mercado_aberto = calendario.mercado_aberto(agora)
    pregao_corr = calendario.pregao_corrente(agora)

    ctx = _get_seletor_context(target_data, agora, mercado_aberto, pregao_corr)
    estado_mercado = ctx["estado_mercado"]
    data_ref = ctx["data_referencia"]
    is_historical = ctx["is_historical"]
    datas_disponiveis = ctx["datas_disponiveis"]
    datas_seletor = ctx["datas_seletor"]
    data_invalida = ctx["data_invalida"]
    _ = (estado_mercado, data_ref, datas_disponiveis, datas_seletor, data_invalida)

    try:
        if is_historical:
            from app.consultor.armazenamento import get_recomendacoes

            hist = get_recomendacoes(target_data or "")

            # format hist to look like calcular_consultor output
            resultados: dict[str, list[Any]] = {
                "Comprar": [],
                "Vender": [],
                "Aguardar": [],
                "No radar": [],
                "Sem sinal": [],
            }
            for row in hist:
                group = row["decisao"]
                if group not in resultados:
                    resultados[group] = []
                # map consensus back, and format
                import ast

                consenso_dict = {}
                try:
                    if row["consenso"]:
                        consenso_dict = ast.literal_eval(row["consenso"])
                except Exception:
                    pass

                resultados[group].append(
                    {
                        "ticker": row["ticker"],
                        "fechamento": row["preco"],
                        "regra": row["regra"],
                        "gatilho": row["gatilho"],
                        "consenso": consenso_dict,
                        "justificativa": "",
                        "motivo": row["regra"],
                        "timestamp": row["timestamp"],
                        "mensagem_confianca": "histórico indisponível (pregão passado)",
                    }
                )
                from app.consultor.armazenamento import get_connection, init_db
                from app.consultor.placar import _calcular_excesso

                init_db()
                c_conn, _ = get_connection()
                try:
                    cur = c_conn.cursor()
                    cur.execute(
                        "SELECT data_pregao FROM consultor_fechamentos ORDER BY data_pregao ASC"
                    )
                    dps = sorted(list(set([x[0] for x in cur.fetchall()])))
                    dp_rec = row["timestamp"][:10]
                    msg = "ainda sem resultado"
                    if dp_rec in dps:
                        idx = dps.index(dp_rec)
                        offset = min(5, len(dps) - 1 - idx)
                        if offset > 0:
                            dp_futuro = dps[idx + offset]
                            cur.execute(
                                "SELECT preco_fechamento FROM consultor_fechamentos WHERE data_pregao = ? AND ticker = ?",
                                (dp_futuro, row["ticker"]),
                            )
                            p_futuro_row = cur.fetchone()
                            cur.execute(
                                "SELECT preco_fechamento FROM consultor_fechamentos WHERE data_pregao = ? AND ticker = ?",
                                (dp_rec, "^BVSP"),
                            )
                            ibov_hoje_row = cur.fetchone()
                            cur.execute(
                                "SELECT preco_fechamento FROM consultor_fechamentos WHERE data_pregao = ? AND ticker = ?",
                                (dp_futuro, "^BVSP"),
                            )
                            ibov_futuro_row = cur.fetchone()

                            if p_futuro_row and ibov_hoje_row and ibov_futuro_row:
                                p_futuro = p_futuro_row[0]
                                ibov_hoje = ibov_hoje_row[0]
                                ibov_futuro = ibov_futuro_row[0]
                                excesso = _calcular_excesso(
                                    row["preco"], p_futuro, ibov_hoje, ibov_futuro
                                )
                                sinal = "+" if excesso > 0 else ""
                                msg = f"{sinal}{excesso * 100:.1f}% contra o IBOV em {offset} pregões"
                finally:
                    c_conn.close()
                resultados[group][-1]["mensagem_confianca"] = msg

            from app.consultor.armazenamento import get_opinioes_historicas

            opinioes_historicas = get_opinioes_historicas(target_data or "")

            dados = {
                "resultados": resultados,
                "ativos_avaliados": len(hist),
                "regras_confianca": {},
                "opinioes_recentes": opinioes_historicas,
                "opinioes_status": {},
            }
        else:
            dados = calcular_consultor()
        consultor_indisponivel = False
        import app.consultor.regras as regras_module

        if "regras_limiares" in dados:
            regras_limiares = dados["regras_limiares"]
        else:
            regras_limiares = {
                "R1_QUEDAS": regras_module.R1_QUEDAS,
                "R1_GATILHO_VOL": regras_module.R1_GATILHO_VOL,
                "R3_IFR_MAX": regras_module.R3_IFR_MAX,
                "R3_IFR_RECUO": regras_module.R3_IFR_RECUO,
                "R4_DISTANCIA_MM200": regras_module.R4_DISTANCIA_MM200,
                "R4_GATILHO_VOL": regras_module.R4_GATILHO_VOL,
                "R5_IFR_MIN": regras_module.R5_IFR_MIN,
                "R5_IFR_MAX": regras_module.R5_IFR_MAX,
            }
    except Exception:
        logger.exception("Consultor indisponível")
        dados = {
            "resultados": {},
            "ativos_avaliados": 0,
            "armazenamento": "sqlite_efemero",
        }
        consultor_indisponivel = True
        regras_limiares = {}

    try:
        from typing import cast, Dict

        dados_dict = cast(Dict[str, Any], dados) if isinstance(dados, dict) else {}
        opinioes_status_data = dados_dict.get("opinioes_status") or {
            "status": "ok",
            "motivo": "",
            "desde": "",
            "ultima_extracao_em": "",
            "materias_processadas": 0,
            "opinioes_gravadas": 0,
            "descartadas": 0,
        }

        has_opinions = (
            len(cast(list, dados_dict.get("opinioes_recentes", []))) > 0
            if dados_dict
            else False
        )

        status = opinioes_status_data.get("status", "ok")
        motivo = opinioes_status_data.get("motivo", "")

        from app.database import get_connection

        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM consultor_fila_materias WHERE processada = 0"
            )
            fila_pendentes = cursor.fetchone()[0]
        except Exception:
            fila_pendentes = 0
        finally:
            conn.close()

        never_extracted = not bool(opinioes_status_data.get("ultima_extracao_em"))

        codigo = "aguardando"
        if status == "sem_chave":
            codigo = "sem_chave"
        elif status == "cota":
            codigo = "cota"
        elif status in ("erro", "invalido"):
            codigo = "erro"
        elif never_extracted:
            codigo = "aguardando"
        elif status == "ok":
            if fila_pendentes > 0:
                codigo = "fila"
            else:
                if opinioes_status_data.get("descartadas", 0) > 0 and not has_opinions:
                    codigo = "descartadas"
                elif not has_opinions:
                    codigo = "sem_materias"
                else:
                    codigo = "ok"

        opinioes_diagnostico = {
            "codigo": codigo,
            "motivo": motivo,
            "desde": opinioes_status_data.get("desde", ""),
            "ultima_extracao_em": opinioes_status_data.get("ultima_extracao_em", ""),
            "materias_processadas": opinioes_status_data.get("materias_processadas", 0),
            "opinioes_gravadas": opinioes_status_data.get("opinioes_gravadas", 0),
            "descartadas": opinioes_status_data.get("descartadas", 0),
            "fila_pendentes": fila_pendentes,
        }
    except Exception:
        opinioes_diagnostico = {"codigo": "erro"}

    from app.consultor.informacoes import construir_informacoes_de

    informacoes_de = construir_informacoes_de(dados) if isinstance(dados, dict) else {}

    return templates.TemplateResponse(
        request=request,
        name="consultor.html",
        context={
            "desatualizada": composicao_esta_desatualizada(),
            "fonte": FONTE_URL,
            "dados": dados,
            "informacoes_de": informacoes_de,
            "consultor_indisponivel": consultor_indisponivel,
            "regras_limiares": regras_limiares,
            "opinioes_diagnostico": opinioes_diagnostico,
            "datas_seletor": datas_seletor,
            "data_referencia": data_ref,
            "is_historical": is_historical,
            "data_invalida": data_invalida,
        },
    )


@app.get("/api/consultor")
def api_consultor(
    request: Request,
    data: str | None = Query(default=None, alias="data"),
    data_str: str | None = None,
):
    exigir_senha(request)

    target_data = data or data_str
    agora = datetime.now(timezone.utc)
    mercado_aberto = calendario.mercado_aberto(agora)
    pregao_corr = calendario.pregao_corrente(agora)

    ctx = _get_seletor_context(target_data, agora, mercado_aberto, pregao_corr)
    if ctx["data_invalida"]:
        return JSONResponse(
            status_code=404, content={"erro": "Data inválida ou fora da janela."}
        )

    is_historical = ctx["is_historical"]

    import time
    from app.consultor.calculador import _consultor_cache_time

    _t0 = time.perf_counter()
    try:
        if is_historical:
            from app.consultor.armazenamento import (
                get_recomendacoes,
                get_opinioes_historicas,
            )

            hist = get_recomendacoes(target_data or "")

            resultados: dict[str, list[Any]] = {
                "Comprar": [],
                "Vender": [],
                "Aguardar": [],
                "No radar": [],
                "Sem sinal": [],
            }
            import ast

            for row in hist:
                group = row["decisao"]
                if group not in resultados:
                    resultados[group] = []
                consenso_dict = {}
                try:
                    if row["consenso"]:
                        consenso_dict = ast.literal_eval(row["consenso"])
                except Exception:
                    pass
                resultados[group].append(
                    {
                        "ticker": row["ticker"],
                        "fechamento": row["preco"],
                        "regra": row["regra"],
                        "gatilho": row["gatilho"],
                        "consenso": consenso_dict,
                        "justificativa": "",
                        "motivo": row["regra"],
                        "timestamp": row["timestamp"],
                        "mensagem_confianca": "histórico indisponível (pregão passado)",
                    }
                )
                from app.consultor.armazenamento import get_connection, init_db
                from app.consultor.placar import _calcular_excesso

                init_db()
                c_conn, _ = get_connection()
                try:
                    cur = c_conn.cursor()
                    cur.execute(
                        "SELECT data_pregao FROM consultor_fechamentos ORDER BY data_pregao ASC"
                    )
                    dps = sorted(list(set([x[0] for x in cur.fetchall()])))
                    dp_rec = row["timestamp"][:10]
                    msg = "ainda sem resultado"
                    if dp_rec in dps:
                        idx = dps.index(dp_rec)
                        offset = min(5, len(dps) - 1 - idx)
                        if offset > 0:
                            dp_futuro = dps[idx + offset]
                            cur.execute(
                                "SELECT preco_fechamento FROM consultor_fechamentos WHERE data_pregao = ? AND ticker = ?",
                                (dp_futuro, row["ticker"]),
                            )
                            p_futuro_row = cur.fetchone()
                            cur.execute(
                                "SELECT preco_fechamento FROM consultor_fechamentos WHERE data_pregao = ? AND ticker = ?",
                                (dp_rec, "^BVSP"),
                            )
                            ibov_hoje_row = cur.fetchone()
                            cur.execute(
                                "SELECT preco_fechamento FROM consultor_fechamentos WHERE data_pregao = ? AND ticker = ?",
                                (dp_futuro, "^BVSP"),
                            )
                            ibov_futuro_row = cur.fetchone()

                            if p_futuro_row and ibov_hoje_row and ibov_futuro_row:
                                p_futuro = p_futuro_row[0]
                                ibov_hoje = ibov_hoje_row[0]
                                ibov_futuro = ibov_futuro_row[0]
                                excesso = _calcular_excesso(
                                    row["preco"], p_futuro, ibov_hoje, ibov_futuro
                                )
                                sinal = "+" if excesso > 0 else ""
                                msg = f"{sinal}{excesso * 100:.1f}% contra o IBOV em {offset} pregões"
                finally:
                    c_conn.close()
                resultados[group][-1]["mensagem_confianca"] = msg
            opinioes_historicas_api = get_opinioes_historicas(target_data or "")
            dados: dict[str, Any] = {
                "resultados": resultados,
                "ativos_avaliados": len(hist),
                "regras_confianca": {},
                "opinioes_recentes": opinioes_historicas_api,
                "opinioes_status": {},
            }
            _usou_cache = False
        else:
            _cache_ts_before = _consultor_cache_time
            dados = calcular_consultor()
            _cache_ts_after = _consultor_cache_time
            _usou_cache = (
                _cache_ts_before == _cache_ts_after
                if _cache_ts_before is not None
                else False
            )
    except Exception:
        _usou_cache = False
        dados = {
            "resultados": {},
            "ativos_avaliados": 0,
            "armazenamento": "sqlite_efemero",
        }

    try:
        opinioes_status_data = (
            dados.get("opinioes_status") if isinstance(dados, dict) else None
        ) or {
            "status": "ok",
            "motivo": "",
            "desde": "",
            "ultima_extracao_em": "",
            "materias_processadas": 0,
            "opinioes_gravadas": 0,
            "descartadas": 0,
        }
        has_opinions = (
            len(dados.get("opinioes_recentes", [])) > 0
            if isinstance(dados, dict)
            else False
        )

        from app.database import get_connection

        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM consultor_fila_materias WHERE processada = 0"
            )
            fila_n = cursor.fetchone()[0]
        except Exception:
            fila_n = 0
        finally:
            conn.close()

        never_extracted = not bool(opinioes_status_data.get("ultima_extracao_em"))
        status = opinioes_status_data.get("status", "ok")
        motivo = opinioes_status_data.get("motivo", "")

        codigo = "aguardando"
        if status == "sem_chave":
            codigo = "sem_chave"
        elif status == "cota":
            codigo = "cota"
        elif status in ("erro", "invalido"):
            codigo = "erro"
        elif never_extracted:
            codigo = "aguardando"
        elif status == "ok":
            if fila_n > 0:
                codigo = "fila"
            else:
                if opinioes_status_data.get("descartadas", 0) > 0 and not has_opinions:
                    codigo = "descartadas"
                elif not has_opinions:
                    codigo = "sem_materias"
                else:
                    codigo = "ok"

        opinioes_diagnostico = {
            "codigo": codigo,
            "motivo": motivo,
            "desde": opinioes_status_data.get("desde", ""),
            "ultima_extracao_em": opinioes_status_data.get("ultima_extracao_em", ""),
            "materias_processadas": opinioes_status_data.get("materias_processadas", 0),
            "opinioes_gravadas": opinioes_status_data.get("opinioes_gravadas", 0),
            "descartadas": opinioes_status_data.get("descartadas", 0),
            "fila_pendentes": fila_n,
        }

        fontes_opiniao = {
            "llm": opinioes_status_data,
            "diagnostico": opinioes_diagnostico,
            "feeds": [
                {
                    "url": "https://www.moneytimes.com.br/feed/",
                    "status": "ok",
                    "ultima_coleta": "",
                },
                {
                    "url": "https://www.infomoney.com.br/feed/",
                    "status": "ok",
                    "ultima_coleta": "",
                },
            ],
            "fila": fila_n,
        }

        # Format opinioes properly for api payload per asset
        opinioes_api = {}
        if isinstance(dados, dict) and "resultados" in dados:
            for cat in dados["resultados"]:
                for item in dados["resultados"][cat]:
                    ticker = item["ticker"]
                    opinioes_api[ticker] = item.get("opinioes", [])

        if isinstance(dados, dict) and "resultados" in dados:
            resultados_dict = dados["resultados"]
        else:
            if isinstance(dados, dict) and "Comprar" in dados:
                resultados_dict = dados
            else:
                resultados_dict = {
                    "Comprar": [],
                    "Vender": [],
                    "Aguardar": [],
                    "Sem sinal": [],
                }
    except Exception:
        resultados_dict = {"Comprar": [], "Vender": [], "Aguardar": [], "Sem sinal": []}

    try:
        ativos_avaliados = (
            dados.get("ativos_avaliados", 0) if isinstance(dados, dict) else 0
        )
    except Exception:
        ativos_avaliados = 0

    from app.consultor.informacoes import construir_informacoes_de

    informacoes_de = construir_informacoes_de(dados) if isinstance(dados, dict) else {}

    return JSONResponse(
        content={
            "atualizado_em": datetime.now().isoformat(),
            "ativos_avaliados": ativos_avaliados,
            "composicao_vigente_ate": COMPOSICAO_VIGENTE_ATE.isoformat(),
            "informacoes_de": informacoes_de,
            "resultados": resultados_dict,
            "fontes_opiniao": fontes_opiniao,
            "opinioes": opinioes_api,
            "duracao_ms": int((time.perf_counter() - _t0) * 1000),
            "cache": _usou_cache,
        }
    )


@app.get("/api/snapshot")
def snapshot(
    data_query: str | None = Query(default=None, alias="data"),
    data_str: str | None = None,
):
    target_data = data_query or data_str
    agora = datetime.now(timezone.utc)
    mercado_aberto = calendario.mercado_aberto(agora)
    pregao_corr = calendario.pregao_corrente(agora)

    ctx = _get_seletor_context(target_data, agora, mercado_aberto, pregao_corr)
    if ctx["data_invalida"]:
        return JSONResponse(
            status_code=404, content={"erro": "Data inválida ou fora da janela."}
        )

    estado_mercado = ctx["estado_mercado"]
    data_ref = ctx["data_referencia"]
    is_historical = ctx["is_historical"]

    import app.banco

    old_data_ref = app.banco._data_referencia_snapshot.get()
    _ = old_data_ref

    if is_historical:
        app.banco._data_referencia_snapshot.set(data_ref)

    resp: dict[str, Any] = {
        "gerado_em": agora.isoformat(),
        "estado_mercado": estado_mercado,
        "data_referencia": data_ref.isoformat(),
        "paineis": {},
    }

    divergencia = get_divergencia_ibov_dolar()
    if divergencia:
        resp["paineis"]["divergencia_ibov_dolar"] = {
            "divergencia_detectada": divergencia.get("divergencia_detectada"),
            "correlacao": divergencia.get("correlacao"),
            "coletado_em": divergencia.get("timestamp"),
            "fonte": divergencia.get("fonte", "yfinance"),
        }

    assimetria = get_latest_assimetria_risco_retorno_data()
    if assimetria:
        resp["paineis"]["assimetria_risco_retorno"] = {
            "coletado_em": assimetria.timestamp.isoformat(),
            "fonte": getattr(assimetria, "fonte", "yfinance"),
            "alertas": json.loads(assimetria.alertas_json),
        }

    data = get_latest_ibovespa_data()
    if data:
        variation_pct = (
            ((data.current_price - data.previous_close) / data.previous_close) * 100
            if data.previous_close
            else 0.0
        )

        history_data = (
            json.loads(data.history_json)
            if data.history_json
            else {"dates": [], "closes": []}
        )

        resp["paineis"]["ibovespa"] = {
            "valor": data.current_price,
            "fechamento_anterior": data.previous_close,
            "variacao_pct": variation_pct,
            "coletado_em": data.timestamp.isoformat(),
            "fonte": getattr(data, "fonte", "brapi"),
            "historico": {
                "datas": history_data.get("dates", []),
                "fechamentos": history_data.get("closes", []),
            },
            "medias_moveis": {
                "mm21": data.mm21,
                "mm200": data.mm200,
            },
        }

    highlights_data = get_latest_highlights_data()
    if highlights_data:
        highs = (
            json.loads(highlights_data.highs_json) if highlights_data.highs_json else []
        )
        lows = (
            json.loads(highlights_data.lows_json) if highlights_data.lows_json else []
        )
        altas_baixas_panel = {
            "coletado_em": highlights_data.timestamp.isoformat(),
            "fonte": getattr(highlights_data, "fonte", "brapi"),
            "altas": highs,
            "baixas": lows,
        }

        up_count = getattr(highlights_data, "up_count", None)
        down_count = getattr(highlights_data, "down_count", None)
        total_count = getattr(highlights_data, "total_count", None)

        if up_count is not None and down_count is not None and total_count:
            altas_baixas_panel["dispersao"] = {
                "em_alta": up_count,
                "em_baixa": down_count,
                "proporcao_alta_pct": (up_count / total_count) * 100,
            }

        resp["paineis"]["altas_baixas"] = altas_baixas_panel

    volume_alerts_data = get_latest_volume_alerts_data()
    if volume_alerts_data:
        alerts = (
            json.loads(volume_alerts_data.alerts_json)
            if volume_alerts_data.alerts_json
            else []
        )
        resp["paineis"]["radar_volume"] = {
            "coletado_em": volume_alerts_data.timestamp.isoformat(),
            "fonte": getattr(volume_alerts_data, "fonte", "yfinance"),
            "alertas": alerts,
        }
    else:
        resp["paineis"]["radar_volume"] = {}

    dolar_corr_data = get_latest_dolar_correlation_data()
    if dolar_corr_data:
        positivas = (
            json.loads(dolar_corr_data.positivas_json)
            if dolar_corr_data.positivas_json
            else []
        )
        negativas = (
            json.loads(dolar_corr_data.negativas_json)
            if dolar_corr_data.negativas_json
            else []
        )
        resp["paineis"]["sensibilidade_dolar"] = {
            "coletado_em": dolar_corr_data.timestamp.isoformat(),
            "fonte": getattr(dolar_corr_data, "fonte", "yfinance"),
            "positivas": positivas,
            "negativas": negativas,
        }
    else:
        resp["paineis"]["sensibilidade_dolar"] = {}

    sensibilidade_juros_data = get_latest_sensibilidade_juros_data()
    if sensibilidade_juros_data:
        try:
            alertas = (
                json.loads(sensibilidade_juros_data.alertas_json)
                if sensibilidade_juros_data.alertas_json
                else []
            )
        except Exception:
            alertas = []
        resp["paineis"]["sensibilidade_juros"] = {
            "fonte": sensibilidade_juros_data.fonte,
            "coletado_em": sensibilidade_juros_data.timestamp.isoformat(),
            "alertas": alertas,
        }
    else:
        resp["paineis"]["sensibilidade_juros"] = {}

    forca_relativa_data = get_latest_forca_relativa_data()
    if forca_relativa_data:
        try:
            maior = json.loads(forca_relativa_data.maior_json)
            menor = json.loads(forca_relativa_data.menor_json)
            resp["paineis"]["forca_relativa"] = {
                "coletado_em": forca_relativa_data.timestamp.isoformat(),
                "fonte": getattr(forca_relativa_data, "fonte", "yfinance"),
                "maior": maior,
                "menor": menor,
            }
        except json.JSONDecodeError:
            resp["paineis"]["forca_relativa"] = {}
    else:
        resp["paineis"]["forca_relativa"] = {}

    escudo_quedas_data = get_latest_escudo_quedas_data()
    if escudo_quedas_data:
        try:
            parsed = json.loads(escudo_quedas_data.top3_json)
            resp["paineis"]["escudo_quedas"] = {
                "coletado_em": escudo_quedas_data.timestamp.isoformat(),
                "fonte": getattr(escudo_quedas_data, "fonte", "yfinance"),
                "qtd_quedas_ibov": parsed.get("qtd_quedas_ibov", 0),
                "top3": parsed.get("top3", []),
            }
        except Exception:
            resp["paineis"]["escudo_quedas"] = {}
    else:
        resp["paineis"]["escudo_quedas"] = {}

    motores_data = get_latest_motores_indice_data()
    if motores_data:
        resp["paineis"]["motores_indice"] = json.loads(motores_data.motores_json)

    clima_global_data = get_latest_clima_global_data()
    if clima_global_data:
        resp["paineis"]["clima_global"] = {
            "coletado_em": clima_global_data.timestamp.astimezone(
                timezone(timedelta(hours=-3))
            ).strftime("%d/%m/%Y %H:%M:%S BRT"),
            "sp500_pct": clima_global_data.sp500_pct,
            "vix_pct": clima_global_data.vix_pct,
            "status": clima_global_data.status,
            "fonte": clima_global_data.fonte,
        }
    else:
        resp["paineis"]["clima_global"] = None
    coesao_data = get_latest_coesao_data()
    if coesao_data:
        resp["paineis"]["coesao"] = {
            "coletado_em": coesao_data.timestamp.isoformat(),
            "fonte": coesao_data.fonte,
            "concordantes": coesao_data.concordantes,
            "total": coesao_data.total,
        }
    else:
        resp["paineis"]["coesao"] = {}

    atrasadas_rally_data = get_latest_atrasadas_rally_data()
    if atrasadas_rally_data:
        try:
            parsed = json.loads(atrasadas_rally_data.top3_json)
            top3 = parsed if isinstance(parsed, list) else []
            resp["paineis"]["atrasadas_rally"] = {
                "coletado_em": atrasadas_rally_data.timestamp.isoformat(),
                "fonte": getattr(atrasadas_rally_data, "fonte", "yfinance"),
                "rally_valido": atrasadas_rally_data.rally_valido,
                "top3": top3,
            }
        except Exception:
            resp["paineis"]["atrasadas_rally"] = {}
    else:
        resp["paineis"]["atrasadas_rally"] = {}

    concentracao_data = get_latest_concentracao_data()
    if concentracao_data:
        try:
            resp["paineis"]["concentracao"] = {
                "coletado_em": concentracao_data.timestamp.isoformat(),
                "fonte": concentracao_data.fonte,
                "resumo": json.loads(concentracao_data.resumo_json),
                "top3": json.loads(concentracao_data.top3_json),
            }
        except Exception:
            resp["paineis"]["concentracao"] = {}

    concentracao_vendedora_data = get_latest_concentracao_vendedora_data()
    if concentracao_vendedora_data:
        try:
            resp["paineis"]["concentracao_vendedora"] = {
                "coletado_em": concentracao_vendedora_data.timestamp.isoformat(),
                "fonte": concentracao_vendedora_data.fonte,
                "resumo": json.loads(concentracao_vendedora_data.resumo_json),
                "top3": json.loads(concentracao_vendedora_data.top3_json),
            }
        except Exception:
            resp["paineis"]["concentracao_vendedora"] = {}
    else:
        resp["paineis"]["concentracao_vendedora"] = {}

    concentracao_setorial_data = get_latest_concentracao_setorial_data()
    if concentracao_setorial_data:
        resp["paineis"]["concentracao_setorial"] = {
            "coletado_em": concentracao_setorial_data.timestamp.astimezone(
                timezone(timedelta(hours=-3))
            ).strftime("%d/%m/%Y %H:%M:%S BRT"),
            "fonte": concentracao_setorial_data.fonte,
            "setor_destaque": concentracao_setorial_data.setor_destaque,
            "variacao_media": concentracao_setorial_data.variacao_media,
            "ha_setor_em_alta": concentracao_setorial_data.variacao_media > 0,
            "setor_lider_volume": concentracao_setorial_data.setor_lider_volume,
            "volume_lider": concentracao_setorial_data.volume_lider,
        }
    else:
        resp["paineis"]["concentracao_setorial"] = {}

    # Maré do mercado (spec 027). Sem coleta válida, chave vazia.
    mare_data = get_latest_mare_data()
    resp["paineis"]["mare"] = mare_servico.snapshot(mare_data) if mare_data else {}

    apetite_risco_data = get_latest_apetite_risco_data()
    if apetite_risco_data:
        resp["paineis"]["apetite_risco"] = {
            "coletado_em": apetite_risco_data.timestamp.isoformat(),
            "fonte": apetite_risco_data.fonte,
            "estado": apetite_risco_data.estado,
            "diferenca": apetite_risco_data.diferenca,
        }
    else:
        resp["paineis"]["apetite_risco"] = {}

    variacao_subita_data = get_latest_variacao_subita_data()
    if variacao_subita_data:
        try:
            alertas = json.loads(variacao_subita_data.alertas_json)
        except Exception:
            alertas = []
        resp["paineis"]["variacao_subita"] = {
            "coletado_em": variacao_subita_data.timestamp.isoformat(),
            "fonte": variacao_subita_data.fonte,
            "alertas": alertas,
        }
    else:
        resp["paineis"]["variacao_subita"] = {}

    rotacao_capital_data = get_latest_rotacao_capital_data()
    if rotacao_capital_data:
        resp["paineis"]["rotacao_capital"] = {
            "coletado_em": rotacao_capital_data.timestamp.isoformat(),
            "fonte": rotacao_capital_data.fonte,
            "estado": rotacao_capital_data.estado,
            "variacoes": {
                "bancos": rotacao_capital_data.var_bancos,
                "commodities": rotacao_capital_data.var_commodities,
            },
        }
    else:
        resp["paineis"]["rotacao_capital"] = {}

    from app.database import get_latest_faca_caindo_data
    from app.database import get_latest_volatilidade_silenciosa_data

    faca_caindo_data = get_latest_faca_caindo_data()
    if faca_caindo_data:
        try:
            alertas = json.loads(faca_caindo_data.alertas_json)
        except Exception:
            alertas = []
        resp["paineis"]["faca_caindo"] = {
            "coletado_em": faca_caindo_data.timestamp.isoformat(),
            "fonte": faca_caindo_data.fonte,
            "alertas": alertas,
        }
    else:
        resp["paineis"]["faca_caindo"] = {}

    compradores_fundo_data = get_latest_compradores_fundo_data()
    if compradores_fundo_data:
        try:
            alertas = json.loads(compradores_fundo_data.alertas_json)
        except Exception:
            alertas = []
        resp["paineis"]["compradores_fundo"] = {
            "coletado_em": compradores_fundo_data.timestamp.isoformat(),
            "fonte": compradores_fundo_data.fonte,
            "alertas": alertas,
        }
    else:
        resp["paineis"]["compradores_fundo"] = {}

    concentracao_ordens_data = get_latest_concentracao_ordens_data()
    if concentracao_ordens_data:
        try:
            alertas = json.loads(concentracao_ordens_data.alertas_json)
        except Exception:
            alertas = []
        resp["paineis"]["concentracao_ordens"] = {
            "fonte": concentracao_ordens_data.fonte,
            "coletado_em": concentracao_ordens_data.timestamp.isoformat(),
            "alertas": alertas,
        }
    else:
        resp["paineis"]["concentracao_ordens"] = {}

    armadilha_abertura_data = get_latest_armadilha_abertura_data()
    if armadilha_abertura_data:
        try:
            alertas = json.loads(armadilha_abertura_data.alertas_json)
        except Exception:
            alertas = []
        resp["paineis"]["armadilha_abertura"] = {
            "coletado_em": armadilha_abertura_data.timestamp.isoformat(),
            "fonte": armadilha_abertura_data.fonte,
            "alertas": alertas,
        }
    else:
        resp["paineis"]["armadilha_abertura"] = {}

    from app.database import (
        get_latest_radar_inflexao_data,
        get_latest_anomalia_peso_data,
        get_latest_radar_short_squeeze_data,
        get_latest_radar_congestionamento_data,
        get_latest_esforco_resultado_data,
        get_latest_radar_divergencia_volume_data,
        get_latest_radar_absorcao_cruzada_data,
        get_latest_fator_peso_pesado_data,
        get_latest_liquidez_abertura_data,
        get_latest_falso_rompimento_data,
    )

    view_di = get_correlacao_di_view_data()
    if view_di:
        resp["paineis"]["correlacao_di"] = {
            "correlacao_intradiaria": view_di.get("correlacao_intradiaria"),
            "correlacao_5d": view_di.get("correlacao_5d"),
            "status_intradiaria": view_di.get("status_intradiaria"),
            "status_5d": view_di.get("status_5d"),
            "coletado_em": view_di.get("coletado_em"),
            "fonte": view_di.get("fonte", "yfinance"),
        }

    radar_short_squeeze_data = get_latest_radar_short_squeeze_data()
    db_radar_congestionamento = get_latest_radar_congestionamento_data()
    if radar_short_squeeze_data:
        try:
            alertas = json.loads(radar_short_squeeze_data.alertas_json)
        except Exception:
            alertas = []
        resp["paineis"]["short_squeeze"] = {
            "coletado_em": radar_short_squeeze_data.timestamp.isoformat(),
            "fonte": radar_short_squeeze_data.fonte,
            "alertas": alertas,
        }
    else:
        resp["paineis"]["short_squeeze"] = []

    resp["paineis"]["radar_congestionamento"] = (
        [
            {
                "ticker": a.ticker,
                "bandwidth": a.bandwidth,
                "sparkline_path": a.sparkline_path,
            }
            for a in db_radar_congestionamento.alertas
        ]
        if db_radar_congestionamento
        else None
    )

    radar_inflexao_data = get_latest_radar_inflexao_data()
    if radar_inflexao_data:
        try:
            alertas = json.loads(radar_inflexao_data.alertas_json)
        except Exception:
            alertas = []
        resp["paineis"]["radar_inflexao"] = {
            "coletado_em": radar_inflexao_data.timestamp.isoformat(),
            "fonte": radar_inflexao_data.fonte,
            "alertas": alertas,
        }
    else:
        resp["paineis"]["radar_inflexao"] = []
    esforco_resultado_data = get_latest_esforco_resultado_data()
    if esforco_resultado_data:
        try:
            alertas = json.loads(esforco_resultado_data.alertas_json)
        except Exception:
            alertas = []
        resp["paineis"]["esforco_resultado"] = alertas
    else:
        resp["paineis"]["esforco_resultado"] = []

    radar_divergencia_volume_data = get_latest_radar_divergencia_volume_data()
    if radar_divergencia_volume_data:
        try:
            alertas = json.loads(radar_divergencia_volume_data.alertas_json)
        except Exception:
            alertas = []
        resp["paineis"]["divergencia_volume"] = alertas
    else:
        resp["paineis"]["divergencia_volume"] = []

    falso_rompimento_data = get_latest_falso_rompimento_data()
    if falso_rompimento_data:
        try:
            alertas = json.loads(falso_rompimento_data.alertas_json)
        except Exception:
            alertas = []
        resp["paineis"]["falso_rompimento"] = alertas
    else:
        resp["paineis"]["falso_rompimento"] = []

    radar_absorcao_cruzada_data = get_latest_radar_absorcao_cruzada_data()
    fator_peso_pesado_data = get_latest_fator_peso_pesado_data()

    if fator_peso_pesado_data:
        resp["paineis"]["fator_peso_pesado"] = {
            "proporcao": fator_peso_pesado_data.proporcao,
            "mercado_lateral": fator_peso_pesado_data.mercado_lateral,
            "coletado_em": fator_peso_pesado_data.timestamp.astimezone(
                timezone(timedelta(hours=-3))
            ).strftime("%d/%m/%Y %H:%M:%S BRT"),
            "fonte": fator_peso_pesado_data.fonte,
        }
    if radar_absorcao_cruzada_data:
        try:
            alertas = json.loads(radar_absorcao_cruzada_data.alertas_json)
        except Exception:
            alertas = []
        resp["paineis"]["radar_absorcao_cruzada"] = {
            "coletado_em": radar_absorcao_cruzada_data.timestamp.isoformat(),
            "fonte": radar_absorcao_cruzada_data.fonte,
            "alertas": alertas,
        }
    else:
        resp["paineis"]["radar_absorcao_cruzada"] = []

    liquidez_abertura_data = get_latest_liquidez_abertura_data()
    if liquidez_abertura_data:
        try:
            alertas = json.loads(liquidez_abertura_data.alertas_json)
        except Exception:
            alertas = []
        resp["paineis"]["liquidez_abertura"] = alertas
    else:
        resp["paineis"]["liquidez_abertura"] = []

    anomalia_peso_data = get_latest_anomalia_peso_data()
    if anomalia_peso_data:
        try:
            alertas = json.loads(anomalia_peso_data.alertas_json)
        except Exception:
            alertas = []
        resp["paineis"]["anomalia_peso"] = alertas
        resp["paineis"]["anomalia_peso"] = []

    anomalia_peso_data = get_latest_anomalia_peso_data()
    if anomalia_peso_data:
        try:
            alertas = json.loads(anomalia_peso_data.alertas_json)
        except Exception:
            alertas = []
        resp["paineis"]["anomalia_peso"] = alertas
    else:
        resp["paineis"]["anomalia_peso"] = []

    sobrevivencia_semanal_data = get_latest_sobrevivencia_semanal_data()
    if sobrevivencia_semanal_data:
        try:
            alertas = json.loads(sobrevivencia_semanal_data.alertas_json)
        except Exception:
            alertas = []
        resp["paineis"]["sobrevivencia_semanal"] = {
            "coletado_em": sobrevivencia_semanal_data.timestamp.isoformat(),
            "fonte": sobrevivencia_semanal_data.fonte,
            "alertas": alertas,
        }
    else:
        resp["paineis"]["sobrevivencia_semanal"] = {}

    volatilidade_silenciosa_data = get_latest_volatilidade_silenciosa_data()
    if volatilidade_silenciosa_data:
        try:
            alertas = json.loads(volatilidade_silenciosa_data.alertas_json)
        except Exception:
            alertas = []
        resp["paineis"]["volatilidade_silenciosa"] = {
            "coletado_em": volatilidade_silenciosa_data.timestamp.isoformat(),
            "fonte": volatilidade_silenciosa_data.fonte,
            "alertas": alertas,
        }
    else:
        resp["paineis"]["volatilidade_silenciosa"] = {}

    anomalias_spread_data = get_latest_radar_anomalias_spread_data()
    if anomalias_spread_data:
        try:
            alertas = json.loads(anomalias_spread_data.alertas_json)
            resp["paineis"]["anomalias_spread"] = alertas
        except Exception:
            resp["paineis"]["anomalias_spread"] = []
    else:
        resp["paineis"]["anomalias_spread"] = []

    exaustao_queda = None
    exaustao_queda_data = get_latest_exaustao_queda_data()
    if exaustao_queda_data:
        alertas = json.loads(exaustao_queda_data.alertas_json)
        if alertas:
            exaustao_queda = {
                "coletado_em": exaustao_queda_data.timestamp.astimezone(
                    timezone(timedelta(hours=-3))
                ).strftime("%d/%m/%Y %H:%M:%S BRT"),
                "fonte": exaustao_queda_data.fonte,
                "alertas": alertas,
            }
    # unused avoid f841
    if exaustao_queda:
        pass

    exaustao_alta_data = get_latest_exaustao_alta_data()
    if exaustao_alta_data:
        resp["paineis"]["exaustao_alta"] = {
            "coletado_em": exaustao_alta_data.timestamp.isoformat(),
            "fonte": getattr(exaustao_alta_data, "fonte", "yfinance"),
            "alertas": json.loads(exaustao_alta_data.alertas_json),
        }

    exaustao_tendencia_data = get_latest_exaustao_tendencia_data()
    if exaustao_tendencia_data:
        try:
            resp["paineis"]["exaustao_tendencia"] = {
                "coletado_em": exaustao_tendencia_data.timestamp.isoformat(),
                "fonte": getattr(exaustao_tendencia_data, "fonte", "yfinance"),
                "alertas": json.loads(exaustao_tendencia_data.alertas_json),
            }
        except Exception:
            pass

    relogio = get_latest_relogio_volatilidade_data()
    if relogio:
        try:
            alertas = json.loads(relogio.alertas_json)
            resp["paineis"]["relogio_volatilidade"] = {
                "coletado_em": relogio.timestamp.isoformat(),
                "fonte": relogio.fonte,
                "ticker": alertas.get("ticker", ""),
                "variacao": alertas.get("variacao", 0.0),
                "amplitude_percentual": alertas.get("amplitude_percentual", 0.0),
                "minima": alertas.get("minima", 0.0),
                "maxima": alertas.get("maxima", 0.0),
                "status": "pico_as_" + str(alertas.get("pico_horario", "")),
            }
        except Exception:
            resp["paineis"]["relogio_volatilidade"] = {}
    else:
        resp["paineis"]["relogio_volatilidade"] = {}

    anomalia_fechamento = get_radar_anomalia_fechamento_view()
    if anomalia_fechamento and "alertas" in anomalia_fechamento:
        resp["paineis"]["anomalia_fechamento"] = anomalia_fechamento

    resp["consultor"] = {
        "atualizado_em": datetime.now(timezone(timedelta(hours=-3))).isoformat(),
        "ativos_avaliados": len(CARTEIRA_IBOVESPA),
        "composicao_vigente_ate": COMPOSICAO_VIGENTE_ATE.isoformat(),
    }

    if is_historical:
        app.banco._data_referencia_snapshot.set(old_data_ref)
    return resp


@app.get("/", response_class=HTMLResponse)
async def index(
    request: Request,
    data: str | None = Query(default=None, alias="data"),
    data_str: str | None = None,
):
    target_data = data or data_str
    agora = datetime.now(timezone.utc)
    mercado_aberto = calendario.mercado_aberto(agora)
    pregao_corr = calendario.pregao_corrente(agora)

    ctx = _get_seletor_context(target_data, agora, mercado_aberto, pregao_corr)
    estado_mercado = ctx["estado_mercado"]
    data_ref = ctx["data_referencia"]
    is_historical = ctx["is_historical"]
    datas_disponiveis = ctx["datas_disponiveis"]
    datas_seletor = ctx["datas_seletor"]
    data_invalida = ctx["data_invalida"]

    import app.banco

    # Store old values to restore
    old_data_ref = app.banco._data_referencia_snapshot.get()
    _ = old_data_ref

    if is_historical:
        app.banco._data_referencia_snapshot.set(data_ref)

    motores_data = get_latest_motores_indice_data()
    motores_cards = json.loads(motores_data.motores_json) if motores_data else None

    clima_global_data = get_latest_clima_global_data()
    clima_global = None
    correlacao_di = get_correlacao_di_view_data()
    if clima_global_data:
        clima_global = {
            "coletado_em": clima_global_data.timestamp.astimezone(
                timezone(timedelta(hours=-3))
            ).strftime("%d/%m/%Y %H:%M:%S BRT"),
            "timestamp": clima_global_data.timestamp.astimezone(
                timezone(timedelta(hours=-3))
            ),
            "sp500_pct": clima_global_data.sp500_pct,
            "vix_pct": clima_global_data.vix_pct,
            "status": clima_global_data.status,
            "fonte": clima_global_data.fonte,
        }
    ibovespa_data = get_ibovespa_view_data()

    highlights_data = get_latest_highlights_data()
    highs_dict = {}
    if (
        highlights_data
        and highlights_data.total_count
        and highlights_data.up_count is not None
    ):
        highs_dict["dispersion_pct"] = (
            highlights_data.up_count / highlights_data.total_count
        ) * 100

    apetite_risco_data = get_latest_apetite_risco_data()
    risco_dict = {}
    if apetite_risco_data:
        risco_dict["estado"] = apetite_risco_data.estado

    data_ibov = get_ibovespa_view_data()
    highlights = get_highlights_view_data()
    volume_alerts = get_volume_alerts_view_data()
    dolar_correlation = get_dolar_correlation_view_data()
    sensibilidade_juros = get_sensibilidade_juros_view_data()
    forca_relativa = get_forca_relativa_view_data()
    escudo_quedas = get_escudo_quedas_view_data()

    manchete = gerar_manchete(ibovespa_data, highs_dict, risco_dict)

    coesao = get_coesao_view_data()
    atrasadas_rally = get_atrasadas_rally_view_data()

    concentracao = get_concentracao_view_data()
    concentracao_vendedora = get_concentracao_vendedora_view_data()

    apetite_risco = get_apetite_risco_view_data()
    concentracao_setorial_data = get_latest_concentracao_setorial_data()
    concentracao_setorial = None
    if concentracao_setorial_data:
        concentracao_setorial = {
            "setor_destaque": concentracao_setorial_data.setor_destaque,
            "variacao_media": concentracao_setorial_data.variacao_media,
            "coletado_em": concentracao_setorial_data.timestamp.astimezone(
                timezone(timedelta(hours=-3))
            ).strftime("%d/%m/%Y %H:%M:%S BRT"),
            "fonte": concentracao_setorial_data.fonte,
            "setor_lider_volume": concentracao_setorial_data.setor_lider_volume,
            "volume_lider": concentracao_setorial_data.volume_lider,
        }

    variacao_subita = get_variacao_subita_view_data()
    radar_anomalia_fechamento = get_radar_anomalia_fechamento_view()
    rotacao_capital = get_rotacao_capital_view()
    faca_caindo = get_faca_caindo_view()
    compradores_fundo = get_compradores_fundo_view()
    armadilha_abertura = get_armadilha_abertura_view()
    from app.database import (
        get_latest_radar_inflexao_data,
        get_latest_anomalia_peso_data,
        get_latest_radar_congestionamento_data,
        get_latest_esforco_resultado_data,
        get_latest_radar_divergencia_volume_data,
        get_latest_radar_absorcao_cruzada_data,
        get_latest_fator_peso_pesado_data,
        get_latest_liquidez_abertura_data,
        get_latest_falso_rompimento_data,
        get_latest_concentracao_ordens_data,
    )

    radar_data = get_latest_radar_inflexao_data()
    radar_inflexao = None
    if radar_data:
        try:
            alertas = json.loads(radar_data.alertas_json)
            radar_inflexao = {
                "coletado_em": radar_data.timestamp.astimezone(
                    timezone(timedelta(hours=-3))
                ).strftime("%d/%m/%Y %H:%M:%S BRT"),
                "fonte": radar_data.fonte,
                "alertas": alertas,
            }
        except Exception:
            pass

    sobrevivencia_semanal = get_sobrevivencia_semanal_view()
    volatilidade_silenciosa = get_volatilidade_silenciosa_view()

    mare = mare_servico.get_mare_view()

    from app.services.radar_short_squeeze import get_radar_short_squeeze_view

    short_squeeze = get_radar_short_squeeze_view()
    anomalia_data = get_latest_anomalia_peso_data()
    radar_congestionamento_data = get_latest_radar_congestionamento_data()

    esforco_resultado_data = get_latest_esforco_resultado_data()
    esforco_resultado = None
    if esforco_resultado_data:
        try:
            alertas = json.loads(esforco_resultado_data.alertas_json)
            esforco_resultado = {
                "coletado_em": esforco_resultado_data.timestamp.astimezone(
                    timezone(timedelta(hours=-3))
                ).strftime("%d/%m/%Y %H:%M:%S BRT"),
                "fonte": esforco_resultado_data.fonte,
                "alertas": alertas,
            }
        except Exception:
            pass

    concentracao_ordens_data = get_latest_concentracao_ordens_data()
    concentracao_ordens = None
    if concentracao_ordens_data:
        try:
            alertas = json.loads(concentracao_ordens_data.alertas_json)
        except Exception:
            alertas = []

        def formatar_data(t):
            return t.strftime("%d/%m/%Y %H:%M:%S BRT")

        concentracao_ordens = {
            "alertas": alertas,
            "coletado_em": formatar_data(concentracao_ordens_data.timestamp),
            "fonte": concentracao_ordens_data.fonte,
        }

    exaustao_queda = None
    exaustao_queda_data = get_latest_exaustao_queda_data()
    if exaustao_queda_data:
        alertas = json.loads(exaustao_queda_data.alertas_json)
        if alertas:
            exaustao_queda = {
                "coletado_em": exaustao_queda_data.timestamp.astimezone(
                    timezone(timedelta(hours=-3))
                ).strftime("%d/%m/%Y %H:%M:%S BRT"),
                "fonte": exaustao_queda_data.fonte,
                "alertas": alertas,
            }
    # unused avoid f841
    if exaustao_queda:
        pass

    exaustao_alta_data = get_latest_exaustao_alta_data()
    exaustao_alta = None
    if exaustao_alta_data:
        try:
            alertas = json.loads(exaustao_alta_data.alertas_json)
            exaustao_alta = {
                "coletado_em": exaustao_alta_data.timestamp.astimezone(
                    timezone(timedelta(hours=-3))
                ).strftime("%d/%m/%Y %H:%M:%S BRT"),
                "fonte": exaustao_alta_data.fonte,
                "alertas": alertas,
            }
        except Exception:
            pass

    exaustao_tendencia_data = get_latest_exaustao_tendencia_data()
    exaustao_tendencia = None
    if exaustao_tendencia_data:
        try:
            alertas = json.loads(exaustao_tendencia_data.alertas_json)
            exaustao_tendencia = {
                "coletado_em": exaustao_tendencia_data.timestamp.astimezone(
                    timezone(timedelta(hours=-3))
                ).strftime("%d/%m/%Y %H:%M:%S BRT"),
                "fonte": exaustao_tendencia_data.fonte,
                "alertas": alertas,
            }
        except Exception:
            pass

    falso_rompimento_data = get_latest_falso_rompimento_data()
    falso_rompimento = None
    if falso_rompimento_data:
        try:
            alertas = json.loads(falso_rompimento_data.alertas_json)
            falso_rompimento = {
                "coletado_em": falso_rompimento_data.timestamp.astimezone(
                    timezone(timedelta(hours=-3))
                ).strftime("%d/%m/%Y %H:%M:%S BRT"),
                "fonte": falso_rompimento_data.fonte,
                "alertas": alertas,
            }
        except Exception:
            pass

    radar_absorcao_cruzada_data = get_latest_radar_absorcao_cruzada_data()
    fator_peso_pesado_data_raw = get_latest_fator_peso_pesado_data()
    fator_peso_pesado_data = None
    if fator_peso_pesado_data_raw:
        fator_peso_pesado_data = {
            "proporcao": fator_peso_pesado_data_raw.proporcao,
            "mercado_lateral": fator_peso_pesado_data_raw.mercado_lateral,
            "coletado_em": fator_peso_pesado_data_raw.timestamp.astimezone(
                timezone(timedelta(hours=-3))
            ).strftime("%d/%m/%Y %H:%M:%S BRT"),
            "fonte": fator_peso_pesado_data_raw.fonte,
        }

    radar_absorcao_cruzada = None
    if radar_absorcao_cruzada_data:
        try:
            alertas = json.loads(radar_absorcao_cruzada_data.alertas_json)
            radar_absorcao_cruzada = {
                "coletado_em": radar_absorcao_cruzada_data.timestamp.astimezone(
                    timezone(timedelta(hours=-3))
                ).strftime("%d/%m/%Y %H:%M:%S BRT"),
                "fonte": radar_absorcao_cruzada_data.fonte,
                "alertas": alertas,
            }
        except Exception:
            pass

    liquidez_abertura_data = get_latest_liquidez_abertura_data()
    liquidez_abertura = None
    if liquidez_abertura_data:
        try:
            alertas = json.loads(liquidez_abertura_data.alertas_json)
            liquidez_abertura = {
                "coletado_em": liquidez_abertura_data.timestamp.astimezone(
                    timezone(timedelta(hours=-3))
                ).strftime("%d/%m/%Y %H:%M:%S BRT"),
                "fonte": liquidez_abertura_data.fonte,
                "alertas": alertas,
            }
        except Exception:
            pass

    radar_divergencia_volume_data = get_latest_radar_divergencia_volume_data()
    radar_divergencia_volume = None
    if radar_divergencia_volume_data:
        try:
            alertas = json.loads(radar_divergencia_volume_data.alertas_json)
            radar_divergencia_volume = {
                "coletado_em": radar_divergencia_volume_data.timestamp.astimezone(
                    timezone(timedelta(hours=-3))
                ).strftime("%d/%m/%Y %H:%M:%S BRT"),
                "fonte": radar_divergencia_volume_data.fonte,
                "alertas": alertas,
            }
        except Exception:
            pass
    anomalia_peso = None
    if anomalia_data:
        try:
            alertas = json.loads(anomalia_data.alertas_json)
            anomalia_peso = {
                "coletado_em": anomalia_data.timestamp.astimezone(
                    timezone(timedelta(hours=-3))
                ).strftime("%d/%m/%Y %H:%M:%S BRT"),
                "fonte": anomalia_data.fonte,
                "alertas": alertas,
            }
        except Exception:
            pass

    anomalias_spread_data = get_latest_radar_anomalias_spread_data()
    anomalias_spread = None
    if anomalias_spread_data:
        try:
            alertas = json.loads(anomalias_spread_data.alertas_json)
            anomalias_spread = {
                "alertas": alertas,
                "coletado_em": anomalias_spread_data.timestamp.astimezone(
                    timezone(timedelta(hours=-3))
                ).strftime("%d/%m/%Y %H:%M:%S BRT"),
                "fonte": anomalias_spread_data.fonte,
            }
        except Exception:
            pass

    anomalias_spread_data = get_latest_radar_anomalias_spread_data()
    anomalias_spread = None
    if anomalias_spread_data:
        try:
            alertas = json.loads(anomalias_spread_data.alertas_json)
            anomalias_spread = {
                "alertas": alertas,
                "coletado_em": anomalias_spread_data.timestamp.astimezone(
                    timezone(timedelta(hours=-3))
                ).strftime("%d/%m/%Y %H:%M:%S BRT"),
                "fonte": anomalias_spread_data.fonte,
            }
        except Exception:
            pass
    relogio_data = get_latest_relogio_volatilidade_data()
    relogio = None
    if relogio_data:
        try:
            alertas = json.loads(relogio_data.alertas_json)

            pico_horario = alertas.get("pico_horario", 0)
            hora_str = (
                datetime.fromtimestamp(pico_horario, tz=dt_timezone.utc).strftime(
                    "%H:%M"
                )
                if pico_horario
                else "--:--"
            )
            relogio = {
                "coletado_em": relogio_data.timestamp.astimezone(
                    timezone(timedelta(hours=-3))
                ).strftime("%d/%m/%Y %H:%M:%S BRT"),
                "fonte": relogio_data.fonte,
                "ticker": alertas.get("ticker", ""),
                "variacao": alertas.get("variacao", 0.0),
                "amplitude_percentual": alertas.get("amplitude_percentual", 0.0),
                "hora_str": hora_str,
            }
        except Exception:
            pass

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "datas_seletor": datas_seletor,
            "data_invalida": data_invalida,
            "datas_disponiveis": datas_disponiveis,
            "is_historical": is_historical,
            "estado_mercado": estado_mercado,
            "data_referencia": data_ref,
            "mercado_aberto": mercado_aberto,
            "manchete": manchete,
            "data": data_ibov,
            "highlights": highlights,
            "volume_alerts": volume_alerts,
            "dolar_correlation": dolar_correlation,
            "sensibilidade_juros": sensibilidade_juros,
            "forca_relativa": forca_relativa,
            "escudo_quedas": escudo_quedas,
            "coesao": coesao,
            "atrasadas_rally": atrasadas_rally,
            "concentracao": concentracao,
            "concentracao_vendedora": concentracao_vendedora,
            "apetite_risco": apetite_risco,
            "concentracao_setorial": concentracao_setorial,
            "variacao_subita": variacao_subita,
            "radar_anomalia_fechamento": radar_anomalia_fechamento,
            "rotacao_capital": rotacao_capital,
            "faca_caindo": faca_caindo,
            "compradores_fundo": compradores_fundo,
            "armadilha_abertura": armadilha_abertura,
            "radar_inflexao": radar_inflexao,
            "short_squeeze": short_squeeze,
            "sobrevivencia_semanal": sobrevivencia_semanal,
            "volatilidade_silenciosa": volatilidade_silenciosa,
            "scanner_capitulacao": scanner_capitulacao.view_model(),
            "anomalia_peso": anomalia_peso,
            "radar_congestionamento": radar_congestionamento_data,
            "esforco_resultado": esforco_resultado,
            "radar_divergencia_volume": radar_divergencia_volume,
            "falso_rompimento": falso_rompimento,
            "radar_absorcao_cruzada": radar_absorcao_cruzada,
            "concentracao_ordens": concentracao_ordens,
            "fator_peso_pesado_data": fator_peso_pesado_data,
            "liquidez_abertura": liquidez_abertura,
            "mare": mare,
            "motores_cards": motores_cards,
            "clima_global": clima_global,
            "correlacao_di": correlacao_di,
            "relogio": relogio,
            "anomalias_spread": anomalias_spread,
            "exaustao_tendencia": exaustao_tendencia,
            "exaustao_queda": exaustao_queda,
            "exaustao_alta": exaustao_alta,
        },
    )
