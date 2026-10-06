"""Toda tabela gravada pelo app precisa ser criada no init_db."""

import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import app.database as db


def test_init_db_cria_toda_tabela_que_o_app_grava():
    fonte = Path(db.__file__).read_text()
    gravadas = set(re.findall(r"INSERT INTO (\w+)", fonte))
    conn = sqlite3.connect(db.DB_PATH)
    existentes = {
        r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    conn.close()
    assert gravadas - existentes == set()


def test_sobrevivencia_semanal_grava_e_le():
    dado = db.SobrevivenciaSemanalData(
        timestamp=datetime(2026, 10, 6, 13, tzinfo=timezone.utc),
        alertas_json="[]",
        fonte="mt5",
    )
    db.save_sobrevivencia_semanal_data(dado)
    lido = db.get_latest_sobrevivencia_semanal_data()
    assert lido is not None
    assert lido.fonte == "mt5"
