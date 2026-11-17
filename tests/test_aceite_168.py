"""Aceite da spec 168: o banco local só cria as tabelas que o app usa.

O `setup_db` do `conftest.py` já roda `app.database.init_db()` num SQLite
temporário a cada teste; aqui só se lê o `sqlite_master` dele.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.database import get_connection
from devagent.aceite import exigir_spec_done

APP = Path(__file__).resolve().parent.parent / "app"

LEGADAS = (
    "historico_diario_cache",
    "instrumentacao_coleta_vazia",
    "instrumentacao_coleta_tempo",
    "ibovespa_cache",
    "highlights_cache",
)
INDICES_LEGADOS = (
    "idx_instrumentacao_coleta_vazia_timestamp",
    "idx_instrumentacao_coleta_tempo_timestamp",
    "idx_ibovespa_cache_timestamp",
    "idx_highlights_cache_timestamp",
)
ESPERADAS = {
    "consultor_consenso_yahoo",
    "consultor_consenso_yahoo_status",
    "consultor_fila_materias",
    "consultor_llm_uso",
    "consultor_opinioes",
    "consultor_opinioes_status",
    "series_diarias",
    "simbolos_sem_cotacao",
    "snapshots_paineis",
    "sqlite_sequence",
}


@pytest.fixture(autouse=True)
def _spec_done():
    exigir_spec_done("168")


def _nomes(tipo: str) -> set[str]:
    conn = get_connection()
    try:
        linhas = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = ?", (tipo,)
        ).fetchall()
    finally:
        conn.close()
    return {linha[0] for linha in linhas}


def _fontes_app() -> str:
    return "\n".join(p.read_text(encoding="utf-8") for p in sorted(APP.rglob("*.py")))


def test_init_db_cria_exatamente_as_dez_tabelas():
    tabelas = _nomes("table")
    assert tabelas == ESPERADAS
    assert not tabelas & set(LEGADAS)
    assert not _nomes("index") & set(INDICES_LEGADOS)


def test_toda_tabela_criada_e_lida_ou_gravada():
    fontes = _fontes_app()
    sem_uso = [
        nome
        for nome in sorted(_nomes("table") - {"sqlite_sequence"})
        if not re.search(rf"(FROM|INTO|UPDATE|JOIN)\s+{re.escape(nome)}\b", fontes)
    ]
    assert sem_uso == []


def test_app_nao_cita_as_tabelas_legadas():
    fontes = _fontes_app()
    citadas = [nome for nome in LEGADAS if re.search(rf"\b{nome}\b", fontes)]
    assert citadas == []
