"""Aceite da spec 141: cada card diz de qual pregão é o número."""

from __future__ import annotations

import importlib
import json
import logging
import re
import types
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app import agendador
from app.banco import gravar_snapshot
from app.database import (
    HighlightsData,
    IbovespaData,
    MotoresIndiceData,
    get_latest_ibovespa_data,
    save_highlights_data,
    save_ibovespa_data,
    save_motores_indice_data,
)
from app.main import app
from devagent.aceite import exigir_spec_done

BRT = timezone(timedelta(hours=-3))
client = TestClient(app)


def test_aceite_141_spec_done():
    exigir_spec_done("141")


@pytest.fixture
def relogio(monkeypatch):
    """Fixa o "agora" da página e do snapshot."""

    class Relogio(datetime):
        agora: datetime = datetime(2026, 11, 5, 21, 56, tzinfo=timezone.utc)

        @classmethod
        def now(cls, tz=None):  # type: ignore[override]
            return cls.agora if tz is None else cls.agora.astimezone(tz)

    monkeypatch.setattr("app.main.datetime", Relogio)
    return Relogio


def _brt(dia: int, hora: int, minuto: int = 0, mes: int = 11) -> datetime:
    return datetime(2026, mes, dia, hora, minuto, tzinfo=BRT)


def _ibov(coleta: datetime, ultimo_pregao: str, valor: float = 172288.0) -> None:
    datas = ["2026-11-02", "2026-11-03", ultimo_pregao]
    save_ibovespa_data(
        IbovespaData(
            timestamp=coleta.astimezone(timezone.utc),
            current_price=valor,
            previous_close=171324.0,
            history_json=json.dumps(
                {"dates": datas, "closes": [170000.0, 171324.0, valor]}
            ),
            fonte="mt5",
        )
    )


def _destaques(coleta: datetime, pregao: str) -> None:
    save_highlights_data(
        HighlightsData(
            timestamp=coleta.astimezone(timezone.utc),
            highs_json="[]",
            lows_json="[]",
            fonte="mt5",
            up_count=18,
            down_count=12,
            total_count=30,
            pregao_data=pregao,
        )
    )


def _secao(html: str, titulo: str) -> str:
    m = re.search(
        r"<section[^>]*>\s*<div class=\"cab\">\s*<h2>"
        + re.escape(titulo)
        + r"</h2>.*?</section>",
        html,
        re.S,
    )
    assert m, f"card {titulo!r} não encontrado"
    return m.group(0)


def _cabecalho(html: str) -> str:
    return html.split("<header>", 1)[1].split("</header>", 1)[0]


def test_criterio_pregoes_mistos(relogio):
    """Ibovespa de 04/11 e Dispersão de 05/11: cabeçalho diz pregões mistos."""
    relogio.agora = _brt(5, 18, 56)
    _ibov(_brt(4, 15, 10), "2026-11-04")
    _destaques(_brt(5, 15, 50), "05/11/2026")

    html = client.get("/").text
    assert "Pregões mistos" in _cabecalho(html)
    rodape_ibov = _secao(html, "Ibovespa").split('class="rodape"', 1)[1]
    assert "04/11/2026" in rodape_ibov
    rodape_disp = _secao(html, "Dispersão").split('class="rodape"', 1)[1]
    assert "05/11/2026" in rodape_disp

    paineis = client.get("/api/snapshot").json()["paineis"]
    assert paineis["ibovespa"]["pregao"] == "2026-11-04"
    assert paineis["altas_baixas"]["pregao"] == "2026-11-05"


def test_criterio_coleta_de_ontem_lida_depois_do_fechamento(relogio):
    """Coleta às 15:10 de 04/11 lida às 18:56 de 05/11: nem ao vivo, nem 18:56."""
    relogio.agora = _brt(5, 18, 56)
    _ibov(_brt(4, 15, 10), "2026-11-04")

    html = client.get("/").text
    assert "Ao vivo" not in html
    card = _secao(html, "Ibovespa")
    assert "18:56" not in card
    assert "04/11/2026 15:10 BRT" in card
    assert "Fechamento de 04/11/2026 · pregão anterior" in _cabecalho(html)


@pytest.mark.parametrize("idade, selo", [(31, True), (30, False)])
def test_criterio_ttl_durante_o_pregao(relogio, idade, selo):
    relogio.agora = _brt(5, 14, 0)
    _ibov(relogio.agora - timedelta(minutes=idade), "2026-11-05")

    card = _secao(client.get("/").text, "Ibovespa")
    assert ("selo-desatualizado" in card) is selo
    assert "172.288 pontos" in card


@pytest.mark.parametrize(
    "agora, coleta, dia",
    [
        (_brt(7, 12, 0), _brt(6, 16, 0), "06/11/2026"),  # sábado
        (_brt(20, 14, 0), _brt(19, 16, 0), "19/11/2026"),  # feriado de 20/11
    ],
)
def test_criterio_fim_de_semana_e_feriado_sem_selo(relogio, agora, coleta, dia):
    relogio.agora = agora
    _ibov(coleta, coleta.date().isoformat())

    html = client.get("/").text
    assert "selo-desatualizado" not in _secao(html, "Ibovespa")
    assert f"Fechamento de {dia}" in _cabecalho(html)
    assert "pregão anterior" not in _cabecalho(html)


def test_criterio_motores_com_carimbo(relogio):
    relogio.agora = _brt(5, 14, 0)
    save_motores_indice_data(
        MotoresIndiceData(
            timestamp=_brt(5, 13, 50).astimezone(timezone.utc),
            motores_json=json.dumps([{"nome": "Financeiro", "variacao": 1.83}]),
            fonte="yfinance",
            pregao_data="2026-11-05",
        )
    )
    card = _secao(client.get("/").text, "Motores do Índice")
    assert 'class="rodape"' in card
    assert "Fonte yfinance · 05/11/2026 13:50 BRT" in card

    motores = client.get("/api/snapshot").json()["paineis"]["motores_indice"]
    assert motores["pregao"] == "2026-11-05"
    assert motores["fonte"] == "yfinance"
    assert motores["coletado_em"]
    assert motores["motores"] == [{"nome": "Financeiro", "variacao": 1.83}]


def test_criterio_motores_sem_carimbo_fica_indisponivel(relogio):
    relogio.agora = _brt(5, 14, 0)
    gravar_snapshot(
        "motores_indice",
        _brt(5, 14, 0).date(),
        "ao_vivo",
        "yfinance",
        {"motores_json": json.dumps([{"nome": "Financeiro", "variacao": 1.83}])},
    )
    card = _secao(client.get("/").text, "Motores do Índice")
    assert "Dado indisponível" in card
    assert "1,83%" not in card
    assert "escondido" not in card.split(">", 1)[0]


def test_criterio_falha_parcial_sem_segredo(monkeypatch, caplog):
    chave = "chave-ficticia-141-nao-vaza"
    monkeypatch.setenv("MT5_API_KEY", chave)
    coleta = _brt(5, 14, 0)
    _ibov(coleta, "2026-11-05")
    antes = get_latest_ibovespa_data()
    assert antes is not None

    def _falha():
        raise RuntimeError(f"401 em http://mt5/api?key={chave} header {chave}")

    falso = types.SimpleNamespace(collect_and_save=_falha)
    original = importlib.import_module

    def _importar(nome, *args, **kwargs):
        if nome.startswith("app.collectors."):
            return falso
        return original(nome, *args, **kwargs)

    monkeypatch.setattr(agendador.importlib, "import_module", _importar)

    class Relogio(datetime):
        @classmethod
        def now(cls, tz=None):  # type: ignore[override]
            agora = _brt(5, 14, 20)
            return agora if tz is None else agora.astimezone(tz)

    monkeypatch.setattr("app.agendador.datetime", Relogio)
    agendador.estado["ultimo_erro"] = None
    detalhes: list[str] = []
    caplog.set_level(logging.DEBUG)

    agendador._coletar(detalhes)

    assert chave not in caplog.text
    assert chave not in "\n".join(detalhes)
    assert chave not in (agendador.estado["ultimo_erro"] or "")
    assert "ibovespa" in caplog.text and "RuntimeError" in caplog.text

    depois = get_latest_ibovespa_data()
    assert depois is not None
    assert depois.timestamp == antes.timestamp
