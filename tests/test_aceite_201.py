"""Aceite da spec 201: a manchete é montada num lugar só.

Sem rede: banco temporário do `conftest.py`, relógio fixo em 26/11/2026,
14:00 BRT (pregão aberto). Cada caso grava as linhas do exemplo e compara a
frase de `/api/snapshot` com a de `/`.
"""

from __future__ import annotations

import html
import inspect
import json
import re
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

import app.main
from app.banco import gravar_snapshot
from app.database import (
    ApetiteRiscoData,
    HighlightsData,
    IbovespaData,
    MotoresIndiceData,
    save_apetite_risco_data,
    save_highlights_data,
    save_ibovespa_data,
    save_motores_indice_data,
)
from app.main import app as aplicacao
from devagent.aceite import exigir_spec_done

client = TestClient(aplicacao)
BRT = timezone(timedelta(hours=-3))
COLETA = datetime(2026, 11, 26, 13, 55, tzinfo=BRT)
PREGAO = "2026-11-26"

SEM_DIRECAO = "O mercado opera sem direção definida."
MISTO_SEM_MOTOR = (
    "O mercado opera em alta, mas os indicadores internos mostram sinais mistos "
    "(12 altas e 15 baixas de 30 ações; motores ausentes)."
)
OTIMISMO = "Dia de otimismo generalizado com forte tomada de risco."
INDISPONIVEL = "Resumo do mercado indisponível no momento."


def test_aceite_201_spec_done():
    exigir_spec_done("201")


@pytest.fixture
def relogio(monkeypatch):
    class Relogio(datetime):
        agora: datetime = datetime(2026, 11, 26, 14, 0, tzinfo=BRT)

        @classmethod
        def now(cls, tz=None):  # type: ignore[override]
            return cls.agora if tz is None else cls.agora.astimezone(tz)

    monkeypatch.setattr("app.main.datetime", Relogio)
    return Relogio


def _ibov(atual: float, anterior: float | None) -> None:
    save_ibovespa_data(
        IbovespaData(
            timestamp=COLETA.astimezone(timezone.utc),
            current_price=atual,
            previous_close=anterior,  # type: ignore[arg-type]
            history_json=json.dumps(
                {
                    "dates": ["2026-11-24", "2026-11-25", PREGAO],
                    "closes": [124000.0, 125000.0, atual],
                }
            ),
            fonte="mt5",
        )
    )


def _destaques(altas: int, baixas: int, total: int = 30) -> None:
    save_highlights_data(
        HighlightsData(
            timestamp=COLETA.astimezone(timezone.utc),
            highs_json="[]",
            lows_json="[]",
            fonte="mt5",
            up_count=altas,
            down_count=baixas,
            total_count=total,
            pregao_data=PREGAO,
        )
    )


def _motores(motores: list[dict], carimbo: bool) -> None:
    if carimbo:
        save_motores_indice_data(
            MotoresIndiceData(
                timestamp=COLETA.astimezone(timezone.utc),
                motores_json=json.dumps(motores),
                pregao_data=PREGAO,
            )
        )
    else:
        gravar_snapshot(
            "motores_indice",
            COLETA.date(),
            "ao_vivo",
            "yfinance",
            {"motores_json": json.dumps(motores)},
        )


def _apetite(estado: str) -> None:
    save_apetite_risco_data(
        ApetiteRiscoData(
            timestamp=COLETA.astimezone(timezone.utc), estado=estado, diferenca=1.0
        )
    )


def _parado():
    _ibov(125000.0, 125000.0)
    _destaques(12, 15)


def _motores_sem_carimbo():
    _ibov(125625.0, 125000.0)
    _destaques(12, 15)
    _motores(
        [{"nome": "Vale", "variacao": -1.2}, {"nome": "Petro", "variacao": -0.8}],
        carimbo=False,
    )


def _alta_ampla():
    _ibov(126250.0, 125000.0)
    _destaques(22, 6)
    _apetite("Tomando risco")
    _motores(
        [{"nome": "Vale", "variacao": 1.1}, {"nome": "Petro", "variacao": 0.9}],
        carimbo=True,
    )


def _sem_anterior():
    _ibov(125000.0, None)
    _destaques(12, 15)


def _frase_da_home() -> str:
    m = re.search(r'class="manchete-texto[^"]*">(.*?)</p>', client.get("/").text, re.S)
    assert m, "a home não mostrou a manchete"
    return html.unescape(m.group(1)).strip()


def _manchete_do_snapshot() -> dict:
    return client.get("/api/snapshot").json()["paineis"]["manchete"]


def test_mesma_frase_nas_duas_rotas(relogio):
    _parado()
    manchete = _manchete_do_snapshot()
    assert manchete["texto"] == SEM_DIRECAO
    assert manchete["humor"] == "sem_direcao"
    assert manchete["fonte"] == "composto"
    assert manchete["coletado_em"]
    assert _frase_da_home() == SEM_DIRECAO


def test_motor_sem_carimbo_fica_fora_nas_duas(relogio):
    _motores_sem_carimbo()
    snapshot = _manchete_do_snapshot()["texto"]
    home = _frase_da_home()
    assert snapshot == MISTO_SEM_MOTOR
    assert home == MISTO_SEM_MOTOR
    assert "motores setoriais divergem" not in snapshot + home


@pytest.mark.parametrize(
    ("montar", "esperado"),
    [
        (_parado, SEM_DIRECAO),
        (_motores_sem_carimbo, MISTO_SEM_MOTOR),
        (_alta_ampla, OTIMISMO),
        (_sem_anterior, INDISPONIVEL),
    ],
)
def test_paridade_em_lote(relogio, montar, esperado):
    montar()
    assert _manchete_do_snapshot()["texto"] == esperado
    assert _frase_da_home() == esperado


def test_um_lugar_so():
    fonte = inspect.getsource(app.main)
    assert "gerar_manchete(" not in fonte
    assert inspect.getsource(app.main.snapshot).count("entradas_da_manchete(") == 1
    assert inspect.getsource(app.main.index).count("entradas_da_manchete(") == 1
