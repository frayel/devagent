"""Aceite da spec 200: o consenso do Yahoo sai do Consultor.

Sem rede: o coletor e o módulo de exibição não existem mais, as duas tabelas
não são criadas, `/api/consultor` não traz a chave `consenso_yahoo` e o
`/sistema` não tem o item "Yahoo · consenso".
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.database import get_connection
from app.services import sistema as sistema_servico
from devagent.aceite import exigir_spec_done
from tests.test_aceite_193 import D, SENHA, _arranjo, _cliente

RAIZ = Path(__file__).resolve().parent.parent
APP = RAIZ / "app"
AGORA = datetime(2026, 11, 27, 15, 0, tzinfo=timezone.utc)
PROIBIDOS = ("consultor_yahoo", "consenso_yahoo", "quoteSummary", "getcrumb")


@pytest.fixture(autouse=True)
def _spec_done():
    exigir_spec_done("200")


def test_coletor_e_exibicao_fora():
    assert not (APP / "collectors" / "consultor_yahoo.py").exists()
    assert not (APP / "consultor" / "consenso_yahoo.py").exists()
    citacoes = [
        f"{p.relative_to(RAIZ)}: {termo}"
        for p in sorted(APP.rglob("*.py"))
        for termo in PROIBIDOS
        if termo in p.read_text(encoding="utf-8")
    ]
    assert citacoes == []


def test_tabelas_fora():
    conn = get_connection()
    try:
        tabelas = {
            linha[0]
            for linha in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
    finally:
        conn.close()
    assert "consultor_consenso_yahoo" not in tabelas
    assert "consultor_consenso_yahoo_status" not in tabelas


def test_api_sem_a_chave(monkeypatch):
    _arranjo(monkeypatch, 5)
    res = _cliente().get(f"/api/consultor?data={D}", auth=("consultor", SENHA))
    assert res.status_code == 200
    corpo = res.json()
    resultados = corpo.get("consultor", corpo).get("resultados", {})
    ativos = [
        item
        for tabela in resultados.values()
        if isinstance(tabela, list)
        for item in tabela
        if isinstance(item, dict)
    ]
    assert ativos
    assert all("consenso_yahoo" not in item for item in ativos)


def test_sistema_sem_o_item():
    estado = sistema_servico.montar(
        agora=AGORA,
        inicio=AGORA - timedelta(hours=8),
        remoto={"github": None, "atualizado_em": AGORA.isoformat()},
        sha_local=None,
        banco={
            "tipo": "SQLite",
            "database_url": True,
            "tamanho": "1 MB",
            "latencia_ms": 1,
            "tabelas": 3,
        },
        coleta_ligada=True,
        estado_coleta={"ultima_coleta": AGORA.isoformat()},
        intervalo_coleta=timedelta(minutes=15),
        vazios={},
        horas_vazios=3,
        tempos={},
        fontes={},
        pausa_mt5=None,
        prontas=[],
        historico_pregoes=[],
        ambiente={},
    )
    nomes = [item["nome"] for grupo in estado["grupos"] for item in grupo["itens"]]
    assert nomes
    assert "Yahoo · consenso" not in nomes


def test_template_sem_o_bloco():
    html = (APP / "templates" / "consultor.html").read_text(encoding="utf-8")
    assert "consenso_yahoo" not in html
