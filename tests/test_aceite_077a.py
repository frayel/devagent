"""Aceite da spec 077a: o que ficou no SQLite depois da migração para o Postgres.

Pula enquanto a 077a não é `done` (devagent.aceite). Quando ela fecha:

- o consultor manda SQL de Postgres quando o backend é Postgres (em 23/10 a
  coleta registrava "the query has 0 placeholders but 1 parameters were
  passed", porque `?` e `INSERT OR REPLACE` iam direto para o Neon);
- a página /sistema descreve o banco que a aplicação usa de fato, e não o
  arquivo `data.db` que sobrou da época do SQLite.
"""

from __future__ import annotations

import re
from unittest.mock import MagicMock

import pytest

from devagent.aceite import exigir_spec_done

PLACEHOLDER_SQLITE = re.compile(r"\?")
SINTAXE_SQLITE = re.compile(r"\bINSERT\s+OR\s+(REPLACE|IGNORE)\b", re.IGNORECASE)


class _Gravador:
    """Conexão Postgres falsa que guarda cada (sql, parâmetros) executado."""

    def __init__(self) -> None:
        self.chamadas: list[tuple[str, tuple]] = []
        cursor = MagicMock()
        cursor.fetchone.return_value = None
        cursor.fetchall.return_value = []
        cursor.execute.side_effect = self._executar
        cursor.__enter__.return_value = cursor
        self.cursor = MagicMock(return_value=cursor)
        self.commit = MagicMock()
        self.close = MagicMock()

    def _executar(self, sql, params=()):
        self.chamadas.append((str(sql), tuple(params or ())))


def _conferir_sql(chamadas: list[tuple[str, tuple]], funcao: str) -> None:
    assert chamadas, f"{funcao} não executou SQL nenhum com o backend Postgres"
    for sql, params in chamadas:
        assert not PLACEHOLDER_SQLITE.search(sql), (
            f"{funcao} mandou placeholder `?` ao Postgres: {sql}"
        )
        assert not SINTAXE_SQLITE.search(sql), (
            f"{funcao} mandou sintaxe exclusiva do SQLite ao Postgres: {sql}"
        )
        assert sql.count("%s") == len(params), (
            f"{funcao}: {sql.count('%s')} placeholders e {len(params)} parâmetros: {sql}"
        )


CHAMADAS_CONSULTOR = [
    ("get_llm_uso_hoje", ()),
    ("incrementar_llm_uso", ()),
    ("set_opinioes_status", ("ok", "")),
    ("get_materias_nao_processadas", ()),
    ("marcar_como_processada", ("guid-1",)),
    (
        "save_opiniao",
        (
            "guid-1",
            "PETR4",
            "Casa X",
            "compra",
            42.0,
            "resumo",
            "trecho",
            "2026-10-22",
            "https://exemplo.invalid/materia",
        ),
    ),
]


@pytest.mark.parametrize(("nome", "args"), CHAMADAS_CONSULTOR)
def test_consultor_manda_sql_de_postgres(monkeypatch, nome, args) -> None:
    exigir_spec_done("077a")
    import app.services.consultor_opinioes as modulo

    conexao = _Gravador()
    monkeypatch.setattr(modulo, "get_connection", lambda: (conexao, "postgres"))
    getattr(modulo, nome)(*args)
    _conferir_sql(conexao.chamadas, nome)


def test_diagnostico_descreve_o_postgres_quando_ele_esta_em_uso(monkeypatch) -> None:
    exigir_spec_done("077a")
    import app.banco as banco

    conexao = _Gravador()
    cursor = conexao.cursor.return_value
    cursor.fetchone.return_value = (12345678,)
    monkeypatch.setenv("DATABASE_URL", "postgresql://usuario:segredo@neon.invalid/db")
    monkeypatch.setattr(banco, "get_backend_type", lambda: "postgres")
    monkeypatch.setattr(banco, "get_connection", lambda: (conexao, "postgres"))

    info = banco.diagnostico()

    assert info["tipo"] == "Postgres"
    assert "erro" not in info
    assert "segredo" not in repr(info)


def test_sistema_nao_acusa_sqlite_com_postgres_em_uso() -> None:
    exigir_spec_done("077a")
    from app.services import sistema as s

    info = {
        "tipo": "Postgres",
        "tamanho": "12 MB",
        "latencia_ms": 40,
        "tabelas": 9,
        "database_url": True,
    }
    item = s.verificar_banco(info)
    assert item.nivel == s.OK
    assert "SQLite" not in item.detalhe


def test_sistema_acusa_queda_para_sqlite_com_texto_novo() -> None:
    exigir_spec_done("077a")
    from app.services import sistema as s

    info = {
        "tipo": "SQLite",
        "tamanho": "1 MB",
        "latencia_ms": 2,
        "tabelas": 4,
        "database_url": True,
    }
    item = s.verificar_banco(info)
    assert item.nivel == s.ATENCAO
    assert "073 a 076" not in item.detalhe
