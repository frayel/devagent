from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.services.ibovespa import get_ibovespa_view_data
from app.services.highlights import get_highlights_view_data

app = FastAPI()
templates = Jinja2Templates(directory="app/templates")


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    data = get_ibovespa_view_data()
    highlights = get_highlights_view_data()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"data": data, "highlights": highlights},
    )
