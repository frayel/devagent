from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.services.ibovespa import get_ibovespa_view_data
from app.services.altas_baixas import get_altas_baixas_view_data

app = FastAPI()
templates = Jinja2Templates(directory="app/templates")


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    data = get_ibovespa_view_data()
    altas_baixas_data = get_altas_baixas_view_data()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"data": data, "altas_baixas_data": altas_baixas_data},
    )
