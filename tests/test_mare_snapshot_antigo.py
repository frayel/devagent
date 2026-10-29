"""Regressão da #592: snapshot da Maré gravado antes da spec 123 derrubava `/`.

A spec 123 acrescentou `ativos_json` ao `MareData` como campo obrigatório. Os
snapshots já gravados em produção não tinham a chave, `MareData(**payload)`
levantava TypeError e a página inicial respondia 500.
"""

from datetime import date

from fastapi.testclient import TestClient

from app.banco import gravar_snapshot
from app.database import get_latest_mare_data

PAYLOAD_ANTIGO = {
    "timestamp": "2026-10-28T18:00:00+00:00",
    "valor": 18,
    "fluxo": 12.6,
    "calma": 0.0,
    "volume": 50.0,
    "historico_json": "[]",
    "fonte": "yfinance",
}


def test_snapshot_sem_ativos_json_e_lido_com_heatmap_vazio():
    gravar_snapshot("mare", date(2026, 10, 28), "final", "yfinance", PAYLOAD_ANTIGO)

    dado = get_latest_mare_data()

    assert dado is not None
    assert dado.valor == 18
    assert dado.ativos_json == "[]"


def test_snapshot_com_chave_desconhecida_nao_quebra_a_leitura():
    payload = dict(PAYLOAD_ANTIGO, campo_de_outra_versao=1)
    gravar_snapshot("mare", date(2026, 10, 28), "final", "yfinance", payload)

    assert get_latest_mare_data() is not None


def test_pagina_inicial_responde_com_snapshot_antigo():
    from app.main import app

    gravar_snapshot("mare", date(2026, 10, 28), "final", "yfinance", PAYLOAD_ANTIGO)

    cliente = TestClient(app)

    assert cliente.get("/").status_code == 200
    assert cliente.get("/api/snapshot").status_code == 200
