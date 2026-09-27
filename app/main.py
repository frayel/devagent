import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

import json
from datetime import datetime, timezone
from app.services.ibovespa import get_ibovespa_view_data
from app.services.highlights import get_highlights_view_data
from app.database import get_latest_ibovespa_data
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


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Strict-Transport-Security"] = (
        "max-age=31536000; includeSubDomains"
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
    data = get_latest_ibovespa_data()
    if not data:
        return {"gerado_em": datetime.now(timezone.utc).isoformat(), "paineis": {}}

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

    return {
        "gerado_em": datetime.now(timezone.utc).isoformat(),
        "paineis": {
            "ibovespa": {
                "valor": data.current_price,
                "fechamento_anterior": data.previous_close,
                "variacao_pct": variation_pct,
                "coletado_em": data.timestamp.isoformat(),
                "fonte": getattr(data, "fonte", "brapi"),
                "historico": {
                    "datas": history_data.get("dates", []),
                    "fechamentos": history_data.get("closes", []),
                },
            }
        },
    }


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    data = get_ibovespa_view_data()
    highlights = get_highlights_view_data()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"data": data, "highlights": highlights},
    )
