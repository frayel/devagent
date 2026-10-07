import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates

from app import gauge
from fastapi.staticfiles import StaticFiles

import json
from datetime import datetime, timezone, timedelta
from app.services.ibovespa import get_ibovespa_view_data
from app.services.manchete import gerar_manchete
from app.database import get_latest_highlights_data, get_latest_apetite_risco_data
from app.services.highlights import get_highlights_view_data
from app.services.volume_alerts import get_volume_alerts_view_data
from app.services.dolar_correlation import get_dolar_correlation_view_data
from app.services.forca_relativa import get_forca_relativa_view_data
from app.services.escudo_quedas import get_escudo_quedas_view_data
from app.services.coesao import get_coesao_view_data
from app.services.atrasadas_rally import get_atrasadas_rally_view_data
from app.services.concentracao import get_concentracao_view_data
from app.services.apetite_risco import get_apetite_risco_view_data
from app.services.variacao_subita import get_variacao_subita_view_data
from app.services.rotacao_capital import get_rotacao_capital_view
from app.services.faca_caindo import get_faca_caindo_view
from app.services.compradores_fundo import get_compradores_fundo_view
from app.services.armadilha_abertura import get_armadilha_abertura_view
from app.services.sobrevivencia_semanal import get_sobrevivencia_semanal_view
from app.services.volatilidade_silenciosa import get_volatilidade_silenciosa_view
from app.services import mare as mare_servico
from app.database import (
    get_latest_concentracao_setorial_data,
    get_latest_ibovespa_data,
    get_latest_volume_alerts_data,
    get_latest_dolar_correlation_data,
    get_latest_forca_relativa_data,
    get_latest_escudo_quedas_data,
    get_latest_coesao_data,
    get_latest_atrasadas_rally_data,
    get_latest_concentracao_data,
    get_latest_variacao_subita_data,
    get_latest_rotacao_capital_data,
    get_latest_compradores_fundo_data,
    get_latest_armadilha_abertura_data,
    get_latest_sobrevivencia_semanal_data,
    get_latest_mare_data,
)
from app import agendador


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    tarefa = None
    if agendador.coleta_ligada():
        tarefa = asyncio.create_task(agendador.laco_de_coleta())
    yield
    if tarefa:
        tarefa.cancel()


app = FastAPI(lifespan=lifespan)
templates = Jinja2Templates(directory="app/templates")
# Cálculo dos gauges (spec 026): a macro só posiciona o que sai de app/gauge.py.
templates.env.globals["gauge_dados"] = gauge.dados
templates.env.filters["gauge_pct"] = gauge.gauge_pct
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
        "img-src 'self' data:"
    )
    return response


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/api/coleta")
def coleta():
    """Diagnóstico da coleta automática (última rodada e último erro)."""
    return {"ligada": agendador.coleta_ligada(), **agendador.estado}


@app.get("/api/snapshot")
def snapshot():
    resp = {"gerado_em": datetime.now(timezone.utc).isoformat(), "paineis": {}}

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
    else:
        resp["paineis"]["concentracao"] = {}

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

    return resp


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
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

    manchete = gerar_manchete(ibovespa_data, highs_dict, risco_dict)

    data = get_ibovespa_view_data()
    highlights = get_highlights_view_data()
    volume_alerts = get_volume_alerts_view_data()
    dolar_correlation = get_dolar_correlation_view_data()
    forca_relativa = get_forca_relativa_view_data()
    escudo_quedas = get_escudo_quedas_view_data()
    coesao = get_coesao_view_data()
    atrasadas_rally = get_atrasadas_rally_view_data()
    concentracao = get_concentracao_view_data()

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
        }

    variacao_subita = get_variacao_subita_view_data()
    rotacao_capital = get_rotacao_capital_view()
    faca_caindo = get_faca_caindo_view()
    compradores_fundo = get_compradores_fundo_view()
    armadilha_abertura = get_armadilha_abertura_view()
    sobrevivencia_semanal = get_sobrevivencia_semanal_view()
    volatilidade_silenciosa = get_volatilidade_silenciosa_view()
    mare = mare_servico.get_mare_view()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "manchete": manchete,
            "data": data,
            "highlights": highlights,
            "volume_alerts": volume_alerts,
            "dolar_correlation": dolar_correlation,
            "forca_relativa": forca_relativa,
            "escudo_quedas": escudo_quedas,
            "coesao": coesao,
            "atrasadas_rally": atrasadas_rally,
            "concentracao": concentracao,
            "apetite_risco": apetite_risco,
            "concentracao_setorial": concentracao_setorial,
            "variacao_subita": variacao_subita,
            "rotacao_capital": rotacao_capital,
            "faca_caindo": faca_caindo,
            "compradores_fundo": compradores_fundo,
            "armadilha_abertura": armadilha_abertura,
            "sobrevivencia_semanal": sobrevivencia_semanal,
            "volatilidade_silenciosa": volatilidade_silenciosa,
            "mare": mare,
        },
    )
