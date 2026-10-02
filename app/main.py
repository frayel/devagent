import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

import json
from datetime import datetime, timezone
from app.services.ibovespa import get_ibovespa_view_data
from app.services.highlights import get_highlights_view_data
from app.services.volume_alerts import get_volume_alerts_view_data
from app.services.dolar_correlation import get_dolar_correlation_view_data
from app.services.forca_relativa import get_forca_relativa_view_data
from app.database import (
    get_latest_ibovespa_data,
    get_latest_highlights_data,
    get_latest_volume_alerts_data,
    get_latest_dolar_correlation_data,
    get_latest_forca_relativa_data,
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
app.mount("/static", StaticFiles(directory="app/static"), name="static")


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
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://unpkg.com https://cdn.plot.ly; "
        "style-src 'self' 'unsafe-inline'; "
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

    return resp


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    data = get_ibovespa_view_data()
    highlights = get_highlights_view_data()
    volume_alerts = get_volume_alerts_view_data()
    dolar_correlation = get_dolar_correlation_view_data()
    forca_relativa = get_forca_relativa_view_data()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "data": data,
            "highlights": highlights,
            "volume_alerts": volume_alerts,
            "dolar_correlation": dolar_correlation,
            "forca_relativa": forca_relativa,
        },
    )
