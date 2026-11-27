from typing import Any
from app.banco import get_backend_type


import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi.responses import JSONResponse
from app.consultor import formato
from app.consultor.calculador import calcular_consultor
from app.consultor.placar import consultor_de_pregao_passado
from app.consultor.diagnostico import diagnostico_de_opinioes
from app.consultor.universo import (
    composicao_esta_desatualizada,
    FONTE_URL,
    CARTEIRA_IBOVESPA,
    COMPOSICAO_VIGENTE_ATE,
)
import secrets
from fastapi import HTTPException, status
import os
from fastapi import FastAPI, Request, Query
from app import calendario
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates

from app import gauge
from fastapi.staticfiles import StaticFiles

import json
from datetime import date, datetime, timezone, timedelta
from datetime import timezone as dt_timezone
from app.services.ibovespa import get_ibovespa_view_data
from app.services import carimbo as carimbo_servico
from app.services import destaques as destaques_servico
from app.services import novidades as novidades_servico
from app.services.manchete import entradas_da_manchete
from app.database import get_latest_highlights_data, get_latest_apetite_risco_data
from app.services.highlights import (
    acao_media_api,
    comparar_com_ibovespa,
    get_highlights_view_data,
)
from app.services.volume_alerts import get_volume_alerts_view_data
from app.services import radares as radares_servico
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
    get_latest_rotacao_capital_data,
    get_latest_sobrevivencia_semanal_data,
    get_latest_mare_data,
    get_latest_radar_anomalias_spread_data,
    get_latest_exaustao_tendencia_data,
    get_latest_exaustao_queda_data,
    get_latest_exaustao_alta_data,
)
from app import agendador
from app.collectors.ibovespa import LIMIAR_PCT_REVISAO, LIMIAR_PONTOS_REVISAO
from app.collectors import consultor_opinioes as coletor_opinioes
from app.collectors import fator_peso_pesado as fator_peso_pesado_coletor
from app.collectors import pesos_ibovespa
from app.services import sistema as sistema_servico

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:%(name)s:%(message)s",
)
logger = logging.getLogger(__name__)

# Quando esta instância subiu: o Render reinicia o processo a cada deploy e a
# cada vez que acorda o serviço hibernado (página /sistema, spec 082).
INICIO = datetime.now(timezone.utc)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    from app import banco as banco_module

    # Pool do Postgres (spec 129): abre aqui e fecha no desligamento.
    await asyncio.to_thread(banco_module.abrir_pool)
    tarefas = []
    if agendador.coleta_ligada():
        tarefas.append(asyncio.create_task(agendador.laco_de_coleta()))
        tarefas.append(asyncio.create_task(agendador.laco_das_opinioes()))
    from app.collectors import sistema as monitor_sistema

    if monitor_sistema.monitor_ligado():
        tarefas.append(asyncio.create_task(monitor_sistema.laco_do_monitor()))
    from app.services import validador_gemini

    tarefas.append(asyncio.create_task(validador_gemini.laco_da_validacao()))
    yield
    for tarefa in tarefas:
        tarefa.cancel()
    await asyncio.to_thread(banco_module.fechar_pool)


logger = logging.getLogger(__name__)

app = FastAPI(lifespan=lifespan)
templates = Jinja2Templates(directory="app/templates")
# Cálculo dos gauges (spec 026): a macro só posiciona o que sai de app/gauge.py.
templates.env.globals["gauge_dados"] = gauge.dados
templates.env.filters["gauge_pct"] = gauge.gauge_pct
templates.env.filters["origem_opiniao"] = coletor_opinioes.origem_do_link
# Spec 194: o texto do Fator Peso Pesado sai da tabela única de pesos.
templates.env.globals["pesos_fator_peso_pesado"] = {
    "texto": pesos_ibovespa.texto_pesos(fator_peso_pesado_coletor.TICKERS_PESO),
    "soma": pesos_ibovespa.numero_peso(
        sum(fator_peso_pesado_coletor.TICKERS_PESO.values())
    ),
}


def _dia_brasilia(momento) -> str:
    """`dd/mm` no fuso de Brasília, para a lista Opiniões Recentes (spec 165)."""
    if not isinstance(momento, datetime):
        return "-"
    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=timezone.utc)
    from app.services.carimbo import FUSO

    return momento.astimezone(FUSO).strftime("%d/%m")


templates.env.filters["dia_brasilia"] = _dia_brasilia


def _dia_mes(data_iso) -> str:
    """`AAAA-MM-DD` -> `dd/mm` (spec 190)."""
    texto = str(data_iso or "")
    return f"{texto[8:10]}/{texto[5:7]}" if len(texto) >= 10 else "-"


def _ate_o_alvo(situacao) -> str:
    """Texto da célula Até o alvo da lista Opiniões Recentes (spec 190)."""
    if not isinstance(situacao, dict):
        return "-"
    if situacao.get("estado") == "atingido":
        preco = formato.numero_br(situacao["preco"])
        return f"atingido em {_dia_mes(situacao['data'])} · R$ {preco}"
    distancia = f"{situacao['distancia'] * 100:+.1f}".replace(".", ",")
    return f"faltam {distancia}% · fech. {_dia_mes(situacao['data'])}"


def _metodo_do_alvo(situacao) -> str:
    """O `title` da célula Até o alvo: o alvo, a base e o sentido (spec 190)."""
    if not isinstance(situacao, dict):
        return ""
    alvo = formato.numero_br(situacao["alvo"])
    base = formato.numero_br(situacao["base_preco"])
    return (
        f"Alvo R$ {alvo} · antes da matéria: R$ {base} em "
        f"{_dia_mes(situacao['base_data'])} ({situacao['sentido']})"
    )


templates.env.filters["ate_o_alvo"] = _ate_o_alvo
templates.env.filters["metodo_do_alvo"] = _metodo_do_alvo
templates.env.filters["reais"] = formato.reais
templates.env.filters["numero_br"] = formato.numero_br
templates.env.filters["percentual"] = formato.percentual
templates.env.filters["data_brasilia"] = formato.data_brasilia


def _referencia_do_dia(target_data: str | None) -> datetime | None:
    """O dia pedido às 23:59:59 UTC: a referência da lista histórica (spec 165)."""
    try:
        dia = datetime.strptime(target_data or "", "%Y-%m-%d")
    except ValueError:
        return None
    return dia.replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)


# Rodapé de todas as páginas (spec 156): lido a cada renderização, sem cache.
templates.env.globals["novidades_atualizado_em"] = novidades_servico.data_mais_recente
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
        "script-src 'self' https://cdn.plot.ly/plotly-basic-2.27.0.min.js; "
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
def coleta(request: Request):
    """Diagnóstico da coleta automática (última rodada e último erro)."""
    exigir_senha(request)
    from app.agendador import estado, coleta_ligada
    import os
    from app.banco import get_backend_type

    res = {"ligada": coleta_ligada(), **estado}
    backend = get_backend_type()
    if os.environ.get("RENDER") and backend != "postgres":
        res["aviso"] = "Banco persistente não configurado: dados se perdem ao reiniciar"
    res["banco"] = backend
    return res


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


def _carimbos_criticos(agora: datetime) -> dict[str, dict[str, Any] | None]:
    """Carimbo dos quatro cards críticos da narrativa (spec 141).

    Lê os snapshots do contexto atual (pregão em leitura). Card sem dado fica None.
    """
    from app.database import get_latest_ibovespa_data, get_latest_mare_data

    resultado: dict[str, dict[str, Any] | None] = {
        chave: None for chave in carimbo_servico.CARDS_CRITICOS
    }
    ibov = get_latest_ibovespa_data()
    if ibov:
        ultima_barra = None
        try:
            datas = json.loads(ibov.history_json or "{}").get("dates") or []
            ultima_barra = datas[-1] if datas else None
        except (ValueError, AttributeError):
            ultima_barra = None
        resultado["ibovespa"] = carimbo_servico.carimbo(
            "ibovespa", ibov.timestamp, getattr(ibov, "fonte", ""), agora, ultima_barra
        )
    mare_dado = get_latest_mare_data()
    if mare_dado:
        resultado["mare"] = carimbo_servico.carimbo(
            "mare", mare_dado.timestamp, mare_dado.fonte, agora
        )
    destaques = get_latest_highlights_data()
    if destaques:
        resultado["altas_baixas"] = carimbo_servico.carimbo(
            "altas_baixas",
            destaques.timestamp,
            getattr(destaques, "fonte", ""),
            agora,
            getattr(destaques, "pregao_data", None),
        )
    motores = get_latest_motores_indice_data()
    if motores and motores.timestamp is not None:
        resultado["motores_indice"] = carimbo_servico.carimbo(
            "motores_indice",
            motores.timestamp,
            motores.fonte,
            agora,
            motores.pregao_data,
        )
    return resultado


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
            agora - timedelta(hours=HORAS_VAZIOS), agora=agora
        )
        rodadas = database.get_rodadas_coleta_desde(
            agora - timedelta(hours=HORAS_VAZIOS), agora=agora
        )
        rodada = database.get_ultima_rodada(agora=agora)
        # Critério de poda: uma consulta para a janela de 10 pregões (spec 153).
        historico_poda = banco_module.ler_snapshots_datas(
            "instrumentacao", sistema_servico.ultimos_pregoes(agora)
        )
    except Exception:  # tabelas ainda não criadas: a verificação do banco acusa
        vazios, rodadas, rodada = {}, {}, None
        historico_poda = {}
    try:
        from app.consultor.universo import CARTEIRA_IBOVESPA

        series_consultor: dict[str, Any] | None = {
            "criado_em": banco_module.versao_series(CARTEIRA_IBOVESPA + ["^BVSP"])
        }
    except Exception:  # banco fora: o item do banco já acusa
        series_consultor = None
    entradas: dict[str, Any] = dict(
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
        tempos={},
        rodada=rodada,
        historico_pregoes=banco_module.listar_datas("ibovespa", 30),
        fontes=registro_fontes.fontes(),
        pausa_mt5=mt5_coletor.pausa(),
        prontas=sistema_servico.specs_prontas(),
        monitor_ligado=monitor_sistema.monitor_ligado(),
        modelo_gemini=gemini_modelo.descricao(),
        historico_poda=historico_poda,
        series_consultor=series_consultor,
    )
    estado = sistema_servico.montar(**entradas)
    # Os grupos desta instância (banco, coleta, integrações) só têm dado real
    # aqui; o monitor acompanha os do GitHub. Atualiza o "desde" deles e monta
    # de novo com ele.
    locais = {g["titulo"] for g in estado["grupos"]} - monitor_sistema.GRUPOS_DO_MONITOR
    if locais and monitor_sistema.monitor_ligado():
        monitor_sistema.atualizar_alertas(estado["grupos"], locais)
        entradas["remoto"] = {
            **entradas["remoto"],
            "_alertas_desde": monitor_sistema._alertas_desde,
        }
        estado = sistema_servico.montar(**entradas)
    return estado


@app.get("/api/sistema")
def api_sistema(request: Request):
    exigir_senha(request)
    return estado_do_sistema()


@app.get("/novidades", response_class=HTMLResponse)
def pagina_novidades(request: Request):
    """O que mudou no painel nos últimos 60 dias e onde ver (spec 156)."""
    agora = datetime.now(timezone.utc)
    ctx = _get_seletor_context(
        None, agora, calendario.mercado_aberto(agora), calendario.pregao_corrente(agora)
    )
    return templates.TemplateResponse(
        request=request,
        name="novidades.html",
        context={
            "data": None,
            "datas_seletor": ctx["datas_seletor"],
            "data_referencia": ctx["data_referencia"],
            "is_historical": ctx["is_historical"],
            "data_invalida": ctx["data_invalida"],
            "grupos": novidades_servico.grupos(),
            "janela_dias": novidades_servico.JANELA_DIAS,
        },
    )


def _card_mare_nivel(
    request: Request,
    nivel: str | None,
    data_passada: bool,
    data_ref: date | None = None,
) -> tuple[dict | None, list[dict]]:
    """View do card da Maré no nível escolhido e o seletor (spec 174b).

    Chamada dentro do contexto de leitura da página: numa data passada,
    `ler_snapshot` já lê o `mare_historico` daquele pregão. Marolas lê a
    curva intradiária de hoje ou, numa data passada, a de `data_ref` (175).
    """
    import app.banco

    escolhido = mare_servico.nivel_valido(nivel)
    historico = intradia = None
    hoje = mare_servico.hoje_brt()
    if escolhido != mare_servico.NIVEL_PADRAO:
        historico = app.banco.ler_snapshot("mare_historico")
    elif data_passada and data_ref is not None:
        intradia = mare_servico.buscar_intradia(data_ref, data_passada=True)
    elif not data_passada:
        intradia = mare_servico.buscar_intradia(hoje)
    card = mare_servico.view_nivel(
        mare_servico.get_mare_view(),
        historico,
        escolhido,
        data_passada,
        intradia=intradia,
        hoje=hoje,
    )
    return card, mare_servico.seletor(dict(request.query_params), escolhido)


@app.get("/mare", response_class=HTMLResponse)
def pagina_mare(request: Request, nivel: str | None = Query(default=None)):
    """A Maré numa tela só dela, para deixar aberta (spec 173).

    Mesmas chamadas do painel geral: a view da Maré e o carimbo da spec 141.
    Mostra sempre a leitura mais recente; sem leitura, o card fica indisponível.
    `?nivel=ondas|mare` troca a janela do card (spec 174b).
    """
    import app.banco

    agora = datetime.now(timezone.utc)
    with app.banco.req_snapshot_cache_ctx():
        mare, seletor = _card_mare_nivel(request, nivel, False)
        carimbo = _carimbos_criticos(agora).get("mare")
    return templates.TemplateResponse(
        request=request,
        name="mare.html",
        context={
            "mare": mare,
            "carimbo": carimbo,
            "seletor": seletor,
        },
    )


@app.get("/mare/card", response_class=HTMLResponse)
def fragmento_mare(
    request: Request,
    nivel: str | None = Query(default=None),
    data: str | None = Query(default=None),
):
    """Só o card da Maré no nível pedido, sem página em volta (spec 174b).

    O `ui.js` troca o conteúdo do card por este fragmento ao clicar no seletor.
    Com `data`, lê o pregão pedido como o painel geral.
    """
    import app.banco

    agora = datetime.now(timezone.utc)
    ctx = _get_seletor_context(
        data, agora, calendario.mercado_aberto(agora), calendario.pregao_corrente(agora)
    )
    historico = bool(ctx["is_historical"])
    with (
        app.banco.req_snapshot_cache_ctx(),
        app.banco.lendo_pregao(ctx["data_referencia"] if historico else None),
    ):
        mare, seletor = _card_mare_nivel(
            request, nivel, historico, ctx["data_referencia"]
        )
        carimbo = _carimbos_criticos(agora).get("mare")
    return templates.TemplateResponse(
        request=request,
        name="mare_card.html",
        context={
            "mare": mare,
            "carimbo": carimbo,
            "seletor": seletor,
            "historico": historico,
        },
    )


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
            dados = consultor_de_pregao_passado(
                target_data or "", _referencia_do_dia(target_data)
            )
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

    opinioes_diagnostico = diagnostico_de_opinioes(
        dados if isinstance(dados, dict) else None, is_historical
    )

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
            dados: dict[str, Any] = consultor_de_pregao_passado(
                target_data or "", _referencia_do_dia(target_data)
            )
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

    opinioes_diagnostico = diagnostico_de_opinioes(
        dados if isinstance(dados, dict) else None, is_historical
    )
    fontes_opiniao = {
        "llm": (dados.get("opinioes_status") if isinstance(dados, dict) else None)
        or {
            "status": "ok",
            "motivo": "",
            "desde": "",
            "ultima_extracao_em": "",
            "materias_processadas": 0,
            "opinioes_gravadas": 0,
            "descartadas": 0,
        },
        "diagnostico": opinioes_diagnostico,
        "feeds": coletor_opinioes.status_fontes(),
        "fila": opinioes_diagnostico["fila_pendentes"],
    }

    opinioes_api: dict[str, Any] = {}
    try:
        # Format opinioes properly for api payload per asset
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


# Radares que entram no /api/snapshot com o mesmo molde (spec 184): chave em
# `paineis`, nome do getter em `app.database` e o que sai sem dado ("nd" para
# `{"fonte": "nd", "coletado_em": agora}`, "lista" para `[]`). As formas sem
# dado são parte do contrato publicado (`auditoria/README.md`) e não mudam.
RADARES_MOLDE_UNICO: tuple[tuple[str, str, str], ...] = (
    ("variacao_subita", "get_latest_variacao_subita_data", "nd"),
    ("faca_caindo", "get_latest_faca_caindo_data", "nd"),
    ("compradores_fundo", "get_latest_compradores_fundo_data", "nd"),
    ("concentracao_ordens", "get_latest_concentracao_ordens_data", "nd"),
    ("armadilha_abertura", "get_latest_armadilha_abertura_data", "nd"),
    ("short_squeeze", "get_latest_radar_short_squeeze_data", "lista"),
    ("radar_inflexao", "get_latest_radar_inflexao_data", "lista"),
    ("radar_absorcao_cruzada", "get_latest_radar_absorcao_cruzada_data", "lista"),
)


def _painel_de_alertas(dado: Any, agora: datetime, sem_dado: str) -> Any:
    """Painel de um radar de molde único; um objeto novo a cada chamada."""
    if not dado:
        if sem_dado == "lista":
            return []
        return {"fonte": "nd", "coletado_em": agora.isoformat()}
    try:
        alertas = json.loads(dado.alertas_json)
    except Exception:
        alertas = []
    return {
        "coletado_em": dado.timestamp.isoformat(),
        "fonte": dado.fonte,
        "alertas": alertas,
    }


def _ultimo_alerta_radares(agora: datetime, is_historical: bool) -> dict[str, Any]:
    """Último pregão em que cada radar acendeu, numa só leitura (spec 185).

    Data histórica ou leitura que falha devolvem o resultado sem registro.
    """
    if is_historical:
        return radares_servico.ultimo_alerta_vazio()
    import app.banco as banco_module

    pregoes = radares_servico.janela_pregoes(agora)
    try:
        historico = banco_module.ler_snapshots_datas("instrumentacao", pregoes)
    except Exception:
        logging.getLogger(__name__).exception("leitura da instrumentação falhou")
        return radares_servico.ultimo_alerta_vazio()
    # Spec 199: o mesmo histórico, sem o pregão corrente, decide o "radar raro".
    return {
        **radares_servico.ultimo_alerta(historico, pregoes),
        "anterior": radares_servico.ultimo_alerta(historico, pregoes[1:]),
    }


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

    with (
        app.banco.lendo_pregao(data_ref if is_historical else None),
        app.banco.req_snapshot_cache_ctx(),
    ):
        carimbos = _carimbos_criticos(agora)

        def _pregao(chave: str) -> str | None:
            c = carimbos.get(chave)
            return c["pregao_iso"] if c else None

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

        elif is_historical:
            resp["paineis"]["divergencia_ibov_dolar"] = None
        assimetria = get_latest_assimetria_risco_retorno_data()
        if assimetria:
            resp["paineis"]["assimetria_risco_retorno"] = {
                "coletado_em": assimetria.timestamp.isoformat(),
                "fonte": getattr(assimetria, "fonte", "yfinance"),
                "alertas": json.loads(assimetria.alertas_json),
            }

        elif is_historical:
            resp["paineis"]["assimetria_risco_retorno"] = None
        # O contrato da auditoria exige `fonte` e `coletado_em` em todo painel
        # (issue #872); a contagem vem da instrumentação lida agora (spec 185).
        ultimo_radares = _ultimo_alerta_radares(agora, is_historical)
        resp["paineis"]["radares_ultimo_alerta"] = {
            **radares_servico.ultimo_alerta_api(ultimo_radares),
            "registrados_antes": radares_servico.registrados_antes(ultimo_radares),
            "raros": [],
            "fonte": "instrumentacao",
            "coletado_em": agora.isoformat(),
        }
        data = get_latest_ibovespa_data()
        if data:
            if data.previous_close and data.previous_close > 0:
                variation_pts = data.current_price - data.previous_close
                variation_pct = (variation_pts / data.previous_close) * 100
                fechamento_anterior: float | None = data.previous_close
                revisao_variacao = (
                    abs(variation_pct) > LIMIAR_PCT_REVISAO
                    or abs(variation_pts) >= LIMIAR_PONTOS_REVISAO
                )
                estado_ibov = None
            else:
                variation_pct = None
                fechamento_anterior = None
                revisao_variacao = False
                estado_ibov = "indisponivel"

            history_data = (
                json.loads(data.history_json)
                if data.history_json
                else {"dates": [], "closes": []}
            )

            ibov_dict: dict[str, Any] = {
                "valor": data.current_price,
                "fechamento_anterior": fechamento_anterior,
                "variacao_pct": variation_pct,
                "revisao_variacao": revisao_variacao,
                "coletado_em": data.timestamp.isoformat(),
                "pregao": _pregao("ibovespa"),
                "fonte": getattr(data, "fonte", "yfinance"),
                "historico": {
                    "datas": history_data.get("dates", []),
                    "fechamentos": history_data.get("closes", []),
                },
                "medias_moveis": {
                    "mm21": data.mm21,
                    "mm200": data.mm200,
                },
            }
            if estado_ibov:
                ibov_dict["estado"] = estado_ibov
            resp["paineis"]["ibovespa"] = ibov_dict

        elif is_historical:
            resp["paineis"]["ibovespa"] = None
        highlights_data = get_latest_highlights_data()
        if highlights_data:
            highs = (
                json.loads(highlights_data.highs_json)
                if highlights_data.highs_json
                else []
            )
            lows = (
                json.loads(highlights_data.lows_json)
                if highlights_data.lows_json
                else []
            )
            em_revisao = (
                json.loads(highlights_data.em_revisao_json)
                if getattr(highlights_data, "em_revisao_json", None)
                else []
            )
            altas_baixas_panel = {
                "coletado_em": highlights_data.timestamp.isoformat(),
                "pregao": _pregao("altas_baixas"),
                "fonte": getattr(highlights_data, "fonte", "yfinance"),
                "altas": highs,
                "baixas": lows,
                "em_revisao": em_revisao,
            }
            if getattr(highlights_data, "pregao_data", None):
                altas_baixas_panel["pregao_data"] = highlights_data.pregao_data
            if getattr(highlights_data, "ausentes_count", 0):
                altas_baixas_panel["ausentes_count"] = highlights_data.ausentes_count

            up_count = getattr(highlights_data, "up_count", None)
            down_count = getattr(highlights_data, "down_count", None)
            total_count = getattr(highlights_data, "total_count", None)

            if up_count is not None and down_count is not None and total_count:
                altas_baixas_panel["dispersao"] = {
                    "em_alta": up_count,
                    "em_baixa": down_count,
                    "proporcao_alta_pct": (up_count / total_count) * 100,
                }

            altas_baixas_panel["acao_media"] = acao_media_api(
                _acao_media_dos_dados(highlights_data, data)
            )

            resp["paineis"]["altas_baixas"] = altas_baixas_panel

        elif is_historical:
            resp["paineis"]["altas_baixas"] = None
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
            resp["paineis"]["radar_volume"] = {
                "fonte": "nd",
                "coletado_em": agora.isoformat(),
            }

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
            resp["paineis"]["sensibilidade_dolar"] = {
                "fonte": "nd",
                "coletado_em": agora.isoformat(),
            }

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
            resp["paineis"]["sensibilidade_juros"] = {
                "fonte": "nd",
                "coletado_em": agora.isoformat(),
            }

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
                resp["paineis"]["forca_relativa"] = {
                    "fonte": "nd",
                    "coletado_em": agora.isoformat(),
                }
        else:
            resp["paineis"]["forca_relativa"] = {
                "fonte": "nd",
                "coletado_em": agora.isoformat(),
            }

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
                resp["paineis"]["escudo_quedas"] = {
                    "fonte": "nd",
                    "coletado_em": agora.isoformat(),
                }
        else:
            resp["paineis"]["escudo_quedas"] = {
                "fonte": "nd",
                "coletado_em": agora.isoformat(),
            }

        motores_data = get_latest_motores_indice_data()
        if motores_data:
            # Objeto com carimbo (spec 141); `motores` é a lista que antes ia crua.
            motores_painel: dict[str, Any] = {
                "pregao": _pregao("motores_indice"),
                "coletado_em": motores_data.timestamp.isoformat()
                if motores_data.timestamp
                else None,
                "fonte": motores_data.fonte,
                "motores": json.loads(motores_data.motores_json),
            }
            if motores_data.timestamp is None:
                motores_painel["estado"] = "indisponivel"
            resp["paineis"]["motores_indice"] = motores_painel

        elif is_historical:
            resp["paineis"]["motores_indice"] = None
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
            resp["paineis"]["coesao"] = {
                "fonte": "nd",
                "coletado_em": agora.isoformat(),
            }

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
                resp["paineis"]["atrasadas_rally"] = {
                    "fonte": "nd",
                    "coletado_em": agora.isoformat(),
                }
        else:
            resp["paineis"]["atrasadas_rally"] = {
                "fonte": "nd",
                "coletado_em": agora.isoformat(),
            }

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
                resp["paineis"]["concentracao"] = {
                    "fonte": "nd",
                    "coletado_em": agora.isoformat(),
                }

        elif is_historical:
            resp["paineis"]["concentracao"] = None
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
                resp["paineis"]["concentracao_vendedora"] = {
                    "fonte": "nd",
                    "coletado_em": agora.isoformat(),
                }
        else:
            resp["paineis"]["concentracao_vendedora"] = {
                "fonte": "nd",
                "coletado_em": agora.isoformat(),
            }

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
            resp["paineis"]["concentracao_setorial"] = {
                "fonte": "nd",
                "coletado_em": agora.isoformat(),
            }

        # Maré do mercado (spec 027). Sem coleta válida, chave vazia.
        mare_data = get_latest_mare_data()
        resp["paineis"]["mare"] = (
            {**mare_servico.snapshot(mare_data), "pregao": _pregao("mare")}
            if mare_data
            else {"fonte": "nd", "coletado_em": agora.isoformat()}
        )
        # Ondas e Maré (spec 174a): do histórico gravado uma vez por pregão.
        mare_historico = app.banco.ler_snapshot("mare_historico")
        resp["paineis"]["mare"]["niveis"] = mare_servico.niveis(mare_historico)
        # O que o Ibovespa fez depois de cada faixa (spec 183); sem caso, null.
        resp["paineis"]["mare"]["memoria"] = mare_servico.memoria(
            (mare_historico or {}).get("leituras") or [],
            resp["paineis"]["mare"].get("faixa"),
        )
        # Curva do dia que o Marolas desenha (spec 175); sem dia com dois
        # pontos, null. Sem leitura da Maré, a chave segue vazia (174a).
        if mare_data:
            resp["paineis"]["mare"]["intradia"] = mare_servico.buscar_intradia(
                mare_servico.hoje_brt()
            )

        apetite_risco_data = get_latest_apetite_risco_data()
        if apetite_risco_data:
            resp["paineis"]["apetite_risco"] = {
                "coletado_em": apetite_risco_data.timestamp.isoformat(),
                "fonte": apetite_risco_data.fonte,
                "estado": apetite_risco_data.estado,
                "diferenca": apetite_risco_data.diferenca,
            }
        else:
            resp["paineis"]["apetite_risco"] = {
                "fonte": "nd",
                "coletado_em": agora.isoformat(),
            }

        for chave, nome_getter, sem_dado in RADARES_MOLDE_UNICO:
            resp["paineis"][chave] = _painel_de_alertas(
                getattr(app.database, nome_getter)(), agora, sem_dado
            )

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
            resp["paineis"]["rotacao_capital"] = {
                "fonte": "nd",
                "coletado_em": agora.isoformat(),
            }

        from app.database import get_latest_volatilidade_silenciosa_data

        from app.database import (
            get_latest_anomalia_peso_data,
            get_latest_radar_congestionamento_data,
            get_latest_esforco_resultado_data,
            get_latest_radar_divergencia_volume_data,
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

        elif is_historical:
            resp["paineis"]["correlacao_di"] = None
        db_radar_congestionamento = get_latest_radar_congestionamento_data()
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

        fator_peso_pesado_data = get_latest_fator_peso_pesado_data()

        if fator_peso_pesado_data:
            from app.services.fator_peso_pesado import apresentar as _fpp

            resp["paineis"]["fator_peso_pesado"] = _fpp(fator_peso_pesado_data)
        elif is_historical:
            resp["paineis"]["fator_peso_pesado"] = None
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

        elif is_historical:
            resp["paineis"]["anomalia_peso"] = None
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
            resp["paineis"]["sobrevivencia_semanal"] = {
                "fonte": "nd",
                "coletado_em": agora.isoformat(),
            }

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
            resp["paineis"]["volatilidade_silenciosa"] = {
                "fonte": "nd",
                "coletado_em": agora.isoformat(),
            }

        anomalias_spread_data = get_latest_radar_anomalias_spread_data()
        if anomalias_spread_data:
            try:
                alertas = json.loads(anomalias_spread_data.alertas_json)
                resp["paineis"]["anomalias_spread"] = alertas
            except Exception:
                resp["paineis"]["anomalias_spread"] = []
        else:
            resp["paineis"]["anomalias_spread"] = []

        exaustao_queda_data = get_latest_exaustao_queda_data()
        if exaustao_queda_data:
            alertas = json.loads(exaustao_queda_data.alertas_json)
            resp["paineis"]["exaustao_queda"] = {
                "coletado_em": exaustao_queda_data.timestamp.isoformat(),
                "fonte": exaustao_queda_data.fonte,
                "alertas": alertas,
            }

        elif is_historical:
            resp["paineis"]["exaustao_queda"] = None
        exaustao_alta_data = get_latest_exaustao_alta_data()
        if exaustao_alta_data:
            resp["paineis"]["exaustao_alta"] = {
                "coletado_em": exaustao_alta_data.timestamp.isoformat(),
                "fonte": getattr(exaustao_alta_data, "fonte", "yfinance"),
                "alertas": json.loads(exaustao_alta_data.alertas_json),
            }

        elif is_historical:
            resp["paineis"]["exaustao_alta"] = None
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

        elif is_historical:
            resp["paineis"]["exaustao_tendencia"] = None
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
                resp["paineis"]["relogio_volatilidade"] = {
                    "fonte": "nd",
                    "coletado_em": agora.isoformat(),
                }
        else:
            resp["paineis"]["relogio_volatilidade"] = {
                "fonte": "nd",
                "coletado_em": agora.isoformat(),
            }

        anomalia_fechamento = get_radar_anomalia_fechamento_view()
        if anomalia_fechamento and "alertas" in anomalia_fechamento:
            # O horário bruto só serve à tela (spec 150); o JSON não muda.
            resp["paineis"]["anomalia_fechamento"] = {
                k: v for k, v in anomalia_fechamento.items() if k != "timestamp"
            }

        elif is_historical:
            resp["paineis"]["anomalia_fechamento"] = None

        # Manchete (specs 140 e 201): a mesma montagem da home.
        manchete_obj = entradas_da_manchete(
            data,
            highlights_data,
            getattr(apetite_risco_data, "estado", None) if apetite_risco_data else None,
            motores_data,
            carimbos,
        )
        resp["paineis"]["manchete"] = {
            "humor": manchete_obj.humor,
            "texto": manchete_obj.texto,
            "coletado_em": agora.isoformat(),
            "fonte": "composto",
        }

        payloads_radares = _payloads_radares()
        # Spec 199: os mesmos payloads e o mesmo `classificar` da página.
        resp["paineis"]["radares_ultimo_alerta"]["raros"] = radares_servico.raros_api(
            radares_servico.raros_do_contexto(
                payloads_radares, agora, is_historical, ultimo_radares
            )
        )
        confluencia = radares_servico.confluencia(
            payloads_radares, agora, is_historical
        )
        resp["paineis"]["confluencia_radares"] = {
            "acoes": confluencia["acoes"],
            "excedentes": confluencia["excedentes"],
            "lidos": confluencia["lidos"],
            "horario": confluencia["horario"].isoformat()
            if confluencia["horario"]
            else None,
            # Contrato do snapshot (auditoria/README.md, issue #872): todo
            # painel publica `fonte` e `coletado_em`. O card é composto a
            # partir dos radares e é montado agora, como a manchete.
            "coletado_em": agora.isoformat(),
            "fonte": "composto",
        }
        resp["paineis"]["confluencia_historico"] = _confluencia_historico_api(agora)

        # Spec 156: fora de `paineis` (sem fonte/coletado_em) e independente do ?data=.
        resp["novidades"] = novidades_servico.recentes()

        resp["consultor"] = {
            "atualizado_em": datetime.now(timezone(timedelta(hours=-3))).isoformat(),
            "ativos_avaliados": len(CARTEIRA_IBOVESPA),
            "composicao_vigente_ate": COMPOSICAO_VIGENTE_ATE.isoformat(),
        }

        return resp


def _memoria_confluencia() -> dict[str, Any] | None:
    """A memória da confluência (spec 186), lida no `lendo_pregao` de quem chama."""
    from app.banco import ler_snapshot

    try:
        return radares_servico.memoria_confluencia(
            ler_snapshot("confluencia_historico")
        )
    except Exception:  # noqa: BLE001 - sem memória, o card fica como antes
        logging.getLogger(__name__).exception("Memória da confluência não lida")
        return None


def _frase_memoria_confluencia() -> str:
    return radares_servico.frase_memoria(_memoria_confluencia())


def _confluencia_historico_api(agora: datetime) -> dict[str, Any]:
    """`paineis.confluencia_historico` do `/api/snapshot` (spec 186)."""
    memoria = _memoria_confluencia()
    if memoria is None:
        return {
            "pregoes": 0,
            "de": None,
            "ate": None,
            "ultimo": None,
            "fonte": "composto",
            "coletado_em": agora.isoformat(),
        }
    return {
        "pregoes": memoria["pregoes"],
        "de": memoria["de"],
        "ate": memoria["ate"],
        "ultimo": memoria["ultimo"],
        "fonte": "composto",
        "coletado_em": memoria["coletado_em"] or agora.isoformat(),
    }


def _payloads_radares() -> dict[str, Any]:
    """Os payloads dos 20 radares de `RADARES`, como `index()` os põe no contexto.

    Compartilhado com o `/api/snapshot` (spec 155): os dois leem os mesmos
    getters, dentro do `lendo_pregao` e do cache de quem chama.
    """
    from app.database import (
        get_latest_concentracao_ordens_data,
        get_latest_esforco_resultado_data,
        get_latest_falso_rompimento_data,
        get_latest_liquidez_abertura_data,
        get_latest_radar_absorcao_cruzada_data,
        get_latest_radar_congestionamento_data,
        get_latest_radar_divergencia_volume_data,
        get_latest_radar_inflexao_data,
    )

    def formatar_data(t):
        return t.strftime("%d/%m/%Y %H:%M:%S BRT")

    volume_alerts = get_volume_alerts_view_data()
    variacao_subita = get_variacao_subita_view_data()
    radar_anomalia_fechamento = get_radar_anomalia_fechamento_view()
    faca_caindo = get_faca_caindo_view()
    compradores_fundo = get_compradores_fundo_view()
    armadilha_abertura = get_armadilha_abertura_view()
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
                "timestamp": radar_data.timestamp,
                "alertas": alertas,
            }
        except Exception:
            pass
    from app.services.radar_short_squeeze import get_radar_short_squeeze_view

    short_squeeze = get_radar_short_squeeze_view()
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
                "timestamp": esforco_resultado_data.timestamp,
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

        concentracao_ordens = {
            "alertas": alertas,
            "coletado_em": formatar_data(concentracao_ordens_data.timestamp),
            "fonte": concentracao_ordens_data.fonte,
            "timestamp": concentracao_ordens_data.timestamp,
        }

    exaustao_queda = None
    exaustao_queda_data = get_latest_exaustao_queda_data()
    if exaustao_queda_data:
        try:
            alertas = json.loads(exaustao_queda_data.alertas_json)
            exaustao_queda = {
                "alertas": alertas,
                "coletado_em": formatar_data(exaustao_queda_data.timestamp),
                "fonte": getattr(exaustao_queda_data, "fonte", "yfinance"),
                "timestamp": exaustao_queda_data.timestamp,
            }
        except Exception:
            pass

    exaustao_alta_data = get_latest_exaustao_alta_data()
    exaustao_alta = None
    if exaustao_alta_data:
        try:
            alertas = json.loads(exaustao_alta_data.alertas_json)
            exaustao_alta = {
                "alertas": alertas,
                "coletado_em": formatar_data(exaustao_alta_data.timestamp),
                "fonte": getattr(exaustao_alta_data, "fonte", "yfinance"),
                "timestamp": exaustao_alta_data.timestamp,
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
                "timestamp": exaustao_tendencia_data.timestamp,
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
                "timestamp": falso_rompimento_data.timestamp,
                "alertas": alertas,
            }
        except Exception:
            pass

    radar_absorcao_cruzada_data = get_latest_radar_absorcao_cruzada_data()
    radar_absorcao_cruzada = None
    if radar_absorcao_cruzada_data:
        try:
            alertas = json.loads(radar_absorcao_cruzada_data.alertas_json)
            radar_absorcao_cruzada = {
                "coletado_em": radar_absorcao_cruzada_data.timestamp.astimezone(
                    timezone(timedelta(hours=-3))
                ).strftime("%d/%m/%Y %H:%M:%S BRT"),
                "fonte": radar_absorcao_cruzada_data.fonte,
                "timestamp": radar_absorcao_cruzada_data.timestamp,
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
                "timestamp": liquidez_abertura_data.timestamp,
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
                "timestamp": radar_divergencia_volume_data.timestamp,
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
                "timestamp": anomalias_spread_data.timestamp,
            }
        except Exception:
            pass

    return {
        "volume_alerts": volume_alerts,
        "variacao_subita": variacao_subita,
        "concentracao_ordens": concentracao_ordens,
        "exaustao_alta": exaustao_alta,
        "exaustao_queda": exaustao_queda,
        "exaustao_tendencia": exaustao_tendencia,
        "radar_absorcao_cruzada": radar_absorcao_cruzada,
        "liquidez_abertura": liquidez_abertura,
        "radar_congestionamento": radar_congestionamento_data,
        "faca_caindo": faca_caindo,
        "anomalias_spread": anomalias_spread,
        "short_squeeze": short_squeeze,
        "falso_rompimento": falso_rompimento,
        "radar_divergencia_volume": radar_divergencia_volume,
        "esforco_resultado": esforco_resultado,
        "scanner_capitulacao": scanner_capitulacao.view_model(),
        "armadilha_abertura": armadilha_abertura,
        "compradores_fundo": compradores_fundo,
        "radar_anomalia_fechamento": radar_anomalia_fechamento,
        "radar_inflexao": radar_inflexao,
    }


def _acao_media_dos_dados(highlights_data: Any, ibov_data: Any) -> dict | None:
    """A ação média contra o Ibovespa (spec 196), com os dados lidos do banco.

    Lida no `lendo_pregao` de quem chama: com `?data=`, usa os dois payloads
    daquele pregão. O Ibovespa só entra se a variação existe e não está em
    revisão, pelos mesmos limiares do card do índice.
    """
    if highlights_data is None:
        return None
    ibov_pct: float | None = None
    ibov_ts = None
    ibov_valida = False
    if (
        ibov_data is not None
        and ibov_data.previous_close
        and ibov_data.previous_close > 0
    ):
        pts = ibov_data.current_price - ibov_data.previous_close
        ibov_pct = pts / ibov_data.previous_close * 100
        ibov_ts = ibov_data.timestamp
        ibov_valida = not (
            abs(ibov_pct) > LIMIAR_PCT_REVISAO or abs(pts) >= LIMIAR_PONTOS_REVISAO
        )
    return comparar_com_ibovespa(
        getattr(highlights_data, "media_simples_pct", None),
        getattr(highlights_data, "media_simples_n", None),
        ibov_pct,
        ibov_ts,
        highlights_data.timestamp,
        ibov_valida,
    )


@app.get("/", response_class=HTMLResponse)
def index(
    request: Request,
    data: str | None = Query(default=None, alias="data"),
    data_str: str | None = None,
    vazios: str | None = Query(default=None),
    nivel: str | None = Query(default=None),
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
    with (
        app.banco.req_snapshot_cache_ctx(),
        app.banco.lendo_pregao(data_ref if is_historical else None),
    ):
        carimbos = _carimbos_criticos(agora)
        motores_data = get_latest_motores_indice_data()
        motores_cards = json.loads(motores_data.motores_json) if motores_data else None
        # Motores sem carimbo não mostram percentual solto (spec 141).
        motores_sem_carimbo = bool(motores_cards) and carimbos["motores_indice"] is None
        if motores_sem_carimbo:
            motores_cards = None

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
        ibovespa_data = get_ibovespa_view_data(agora)

        highlights = get_highlights_view_data()
        acao_media = _acao_media_dos_dados(
            get_latest_highlights_data(), get_latest_ibovespa_data()
        )

        apetite_risco = get_apetite_risco_view_data()
        risco_dict = {}
        if apetite_risco:
            risco_dict["estado"] = apetite_risco.get("estado")

        data_ibov = ibovespa_data
        dolar_correlation = get_dolar_correlation_view_data()
        sensibilidade_juros = get_sensibilidade_juros_view_data()
        forca_relativa = get_forca_relativa_view_data()
        escudo_quedas = get_escudo_quedas_view_data()

        manchete = entradas_da_manchete(
            get_latest_ibovespa_data(),
            get_latest_highlights_data(),
            risco_dict.get("estado"),
            motores_data,
            carimbos,
        )

        coesao = get_coesao_view_data()
        atrasadas_rally = get_atrasadas_rally_view_data()

        concentracao = get_concentracao_view_data()
        concentracao_vendedora = get_concentracao_vendedora_view_data()

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

        rotacao_capital = get_rotacao_capital_view()
        from app.database import (
            get_latest_anomalia_peso_data,
            get_latest_fator_peso_pesado_data,
        )

        sobrevivencia_semanal = get_sobrevivencia_semanal_view()
        volatilidade_silenciosa = get_volatilidade_silenciosa_view()

        mare = mare_servico.get_mare_view()
        mare_card, mare_seletor = _card_mare_nivel(
            request, nivel, is_historical, data_ref
        )
        # Depois de cada faixa (specs 183 e 195): card próprio na Visão Geral,
        # fora do card da Maré, então o seletor de nível não o troca.
        mare_historico = app.banco.ler_snapshot("mare_historico")
        memoria_mare = (
            None
            if is_historical and mare_historico is None
            else mare_servico.view_memoria(
                mare_servico.memoria(
                    (mare_historico or {}).get("leituras") or [],
                    mare["faixa"] if mare else None,
                ),
                mare_historico,
            )
        )

        anomalia_data = get_latest_anomalia_peso_data()

        fator_peso_pesado_data_raw = get_latest_fator_peso_pesado_data()
        from app.services.fator_peso_pesado import apresentar as _fpp

        fator_peso_pesado_data = _fpp(fator_peso_pesado_data_raw)

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

        assimetria_data = get_latest_assimetria_risco_retorno_data()
        assimetria_risco_retorno = None
        if assimetria_data:
            try:
                assimetria_risco_retorno = {
                    "coletado_em": assimetria_data.timestamp.astimezone(
                        timezone(timedelta(hours=-3))
                    ).strftime("%d/%m/%Y %H:%M:%S BRT"),
                    "fonte": getattr(assimetria_data, "fonte", "yfinance"),
                    "alertas": json.loads(assimetria_data.alertas_json),
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

        contexto = {
            **_payloads_radares(),
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
            "acao_media": acao_media,
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
            "rotacao_capital": rotacao_capital,
            "sobrevivencia_semanal": sobrevivencia_semanal,
            "volatilidade_silenciosa": volatilidade_silenciosa,
            "anomalia_peso": anomalia_peso,
            "assimetria_risco_retorno": assimetria_risco_retorno,
            "fator_peso_pesado_data": fator_peso_pesado_data,
            "mare": mare,
            "mare_card": mare_card,
            "mare_seletor": mare_seletor,
            "memoria_mare": memoria_mare,
            "motores_cards": motores_cards,
            "motores_sem_carimbo": motores_sem_carimbo,
            "carimbos": carimbos,
            "pregoes_mistos": carimbo_servico.pregoes_mistos(list(carimbos.values())),
            "rotulo_pregao": ""
            if is_historical
            else carimbo_servico.rotulo_cabecalho(
                list(carimbos.values()), agora, mercado_aberto
            ),
            "clima_global": clima_global,
            "correlacao_di": correlacao_di,
            "relogio": relogio,
        }
        ultimo_radares = _ultimo_alerta_radares(agora, is_historical)
        contexto["radares"] = radares_servico.resumo(
            contexto,
            agora,
            is_historical,
            mostrar_vazios=vazios == "1",
            ultimo=ultimo_radares,
        )
        # Spec 199: o radar raro aceso ganha uma linha sob a manchete.
        contexto["manchete_raros"] = radares_servico.frases_raros(
            radares_servico.raros_do_contexto(
                contexto, agora, is_historical, ultimo_radares
            ),
            radares_servico.registrados_antes(ultimo_radares),
        )
        contexto["confluencia"] = radares_servico.confluencia(
            contexto, agora, is_historical
        )
        contexto["confluencia_memoria"] = (
            "" if is_historical else _frase_memoria_confluencia()
        )
        contexto["destaques"] = destaques_servico.faixa(
            highlights,
            contexto["confluencia"],
            carimbos.get("altas_baixas"),
            data_ref.isoformat() if is_historical and data_ref else None,
        )
        return templates.TemplateResponse(
            request=request, name="index.html", context=contexto
        )
