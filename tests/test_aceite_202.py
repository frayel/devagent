"""Aceite da spec 202: a fila de opiniões diz há quanto tempo a mais antiga espera.

Sem rede. O banco do Consultor fica num SQLite em `tmp_path`, como na
`test_aceite_198`: o `get_connection` de `app.consultor.armazenamento` abre esse
arquivo, separado do SQLite local dos painéis.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from devagent.aceite import exigir_spec_done

SENHA = "senha_secreta"
D = "2023-11-01"
AGORA = datetime(2026, 11, 28, 15, 0, tzinfo=timezone.utc)
VAZIO = {"desde": None, "horas": None, "texto": ""}


@pytest.fixture(autouse=True)
def _spec_done():
    exigir_spec_done("202")


@pytest.fixture
def banco(monkeypatch, tmp_path):
    """Abre o banco do Consultor à parte e devolve uma função que monta a fila."""
    from app.consultor import armazenamento

    caminho = tmp_path / "consultor.db"

    def abrir():
        return sqlite3.connect(str(caminho)), "sqlite_efemero"

    monkeypatch.setattr(armazenamento, "get_connection", abrir)
    monkeypatch.setattr(armazenamento, "_consultor_db_initialized", False)
    armazenamento.init_db()
    monkeypatch.setenv("CONSULTOR_SENHA", SENHA)
    import app.consultor.calculador as calc

    monkeypatch.setattr(calc, "_consultor_cache", None)

    def montar(pendentes: list[str], processadas: list[str] | None = None) -> None:
        conn, _ = abrir()
        c = conn.cursor()
        c.execute("DELETE FROM consultor_fila_materias")
        c.execute("DELETE FROM consultor_opinioes")
        c.execute("DELETE FROM consultor_opinioes_status")
        linhas = [(t, 0) for t in pendentes] + [(t, 1) for t in processadas or []]
        for i, (criado, processada) in enumerate(linhas):
            c.execute(
                "INSERT INTO consultor_fila_materias (guid, titulo, descricao, conteudo, "
                "data_publicacao, link, tickers_citados, criado_em, processada) "
                "VALUES (?, ?, '', '', ?, '', '[]', ?, ?)",
                (f"g{i}", f"Matéria {i}", criado, criado, processada),
            )
        c.execute(
            "INSERT INTO consultor_opinioes_status (status, motivo, desde, "
            "ultima_extracao_em, materias_processadas, opinioes_gravadas, descartadas) "
            "VALUES ('ok', '', '2026-11-25T14:00:00Z', '2026-11-25T14:00:00Z', 3, 0, 0)"
        )
        conn.commit()
        conn.close()

    return montar


def _cliente() -> TestClient:
    from app.main import app

    return TestClient(app)


def _iso(d: datetime) -> str:
    return d.isoformat()


def test_fila_pendente_desde_ignora_processadas(banco):
    from app.consultor.armazenamento import fila_pendente_desde

    pendentes = ["2026-11-28T10:00:00+00:00"] + ["2026-11-28T12:00:00+00:00"] * 6
    banco(pendentes, ["2026-11-25T08:00:00+00:00"])
    assert fila_pendente_desde() == "2026-11-28T10:00:00+00:00"

    banco([], ["2026-11-25T08:00:00+00:00"])
    assert fila_pendente_desde() is None


@pytest.mark.parametrize(
    ("n", "mais_antiga", "horas", "texto"),
    [
        (7, "2026-11-28T10:00:00+00:00", 5.0, "há 5 h"),
        (1, "2026-11-28T14:20:00+00:00", 0.7, "há 40 min"),
        (3, "2026-11-26T09:00:00+00:00", 54.0, "há 2 dias"),
    ],
)
def test_idade_da_fila_da_tabela(banco, n, mais_antiga, horas, texto):
    from app.consultor.diagnostico import idade_da_fila

    banco([mais_antiga] + ["2026-11-28T14:50:00+00:00"] * (n - 1))
    assert idade_da_fila(AGORA) == {
        "desde": mais_antiga,
        "horas": horas,
        "texto": texto,
    }


def test_idade_da_fila_vazia(banco):
    from app.consultor.diagnostico import idade_da_fila

    banco([], ["2026-11-25T08:00:00+00:00"])
    assert idade_da_fila(AGORA) == VAZIO


def test_erro_de_banco_nao_derruba(banco, monkeypatch):
    from app.consultor import armazenamento
    from app.consultor.diagnostico import idade_da_fila

    banco(["2026-11-28T10:00:00+00:00"])

    def falha():
        raise RuntimeError("banco fora do ar")

    monkeypatch.setattr(armazenamento, "fila_pendente_desde", falha)
    assert idade_da_fila(AGORA) == VAZIO
    res = _cliente().get("/api/consultor", auth=("consultor", SENHA))
    assert res.status_code == 200
    assert res.json()["fontes_opiniao"]["fila_idade"] == VAZIO


def test_pagina_e_json_mostram_a_idade(banco):
    agora = datetime.now(timezone.utc)
    mais_antiga = agora - timedelta(hours=5, minutes=5)
    banco([_iso(mais_antiga)] + [_iso(agora)] * 6)

    cliente = _cliente()
    res = cliente.get("/consultor", auth=("consultor", SENHA))
    assert res.status_code == 200
    assert (
        "7 matérias na fila, a próxima extração é na próxima rodada. "
        "A mais antiga espera há 5 h."
    ) in res.text
    assert "Matérias com mais de 3 dias" not in res.text

    res = cliente.get("/api/consultor", auth=("consultor", SENHA))
    assert res.status_code == 200
    idade = res.json()["fontes_opiniao"]["fila_idade"]
    assert idade["texto"] == "há 5 h"
    assert 5.0 <= idade["horas"] <= 5.2
    assert idade["desde"] == _iso(mais_antiga)


def test_pagina_avisa_o_descarte_depois_de_48_h(banco):
    agora = datetime.now(timezone.utc)
    banco([_iso(agora - timedelta(hours=54))] + [_iso(agora)] * 2)

    res = _cliente().get("/consultor", auth=("consultor", SENHA))
    assert res.status_code == 200
    assert (
        "A mais antiga espera há 2 dias. "
        "Matérias com mais de 3 dias saem da fila sem extração."
    ) in res.text


def test_pregao_passado_nao_le_a_idade(banco, monkeypatch):
    import app.main
    from app.consultor import armazenamento

    banco(["2026-11-28T10:00:00+00:00"])
    monkeypatch.setattr(
        app.main, "obter_pregoes_disponiveis", lambda a, b, c: [D, "2023-11-02"]
    )

    def explode():
        raise AssertionError("fila_pendente_desde chamada no pregão passado")

    monkeypatch.setattr(armazenamento, "fila_pendente_desde", explode)
    chamadas = []
    original = app.main.idade_da_fila
    monkeypatch.setattr(
        app.main,
        "idade_da_fila",
        lambda agora: chamadas.append(agora) or original(agora),
    )

    cliente = _cliente()
    res = cliente.get(f"/consultor?data={D}", auth=("consultor", SENHA))
    assert res.status_code == 200
    assert "A mais antiga espera" not in res.text

    res = cliente.get(f"/api/consultor?data={D}", auth=("consultor", SENHA))
    assert res.status_code == 200
    assert res.json()["fontes_opiniao"]["fila_idade"]["desde"] is None
    assert chamadas == []
