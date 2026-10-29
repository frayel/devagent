"""Pool de conexões do Postgres (spec 129)."""

from datetime import date
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app import banco
from app.services.sistema import ATENCAO, OK, verificar_banco


class PoolFalso:
    """Imita o `ConnectionPool`: reaproveita conexões devolvidas, até `max_size`."""

    def __init__(self, max_size: int = banco.POOL_MAX):
        self.max_size = max_size
        self.livres: list = []
        self.emprestadas: set = set()
        self.conectadas = 0
        self.devolvidas = 0
        self.fechado = False

    def _conectar(self):
        self.conectadas += 1
        conn = MagicMock(name=f"conn{self.conectadas}")
        cursor = conn.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = ({"valor": 1},)
        return conn

    def getconn(self):
        if self.livres:
            conn = self.livres.pop()
        elif len(self.emprestadas) < self.max_size:
            conn = self._conectar()
        else:
            raise AssertionError("pool esgotado")
        self.emprestadas.add(conn)
        return conn

    def putconn(self, conn):
        self.emprestadas.remove(conn)
        self.livres.append(conn)
        self.devolvidas += 1

    def close(self):
        self.fechado = True

    def get_stats(self):
        return {
            "connections_num": self.conectadas,
            "connections_ms": 40 * self.conectadas,
        }


@pytest.fixture
def pool(monkeypatch):
    falso = PoolFalso()
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@banco/x")
    monkeypatch.setattr(banco, "get_backend_type", lambda: "postgres")
    monkeypatch.setattr(banco, "_criar_pool", lambda db_url: falso)
    monkeypatch.setattr(banco, "_db_initialized", True)
    monkeypatch.setattr(banco, "_pool", None)
    yield falso
    banco._pool = None


def test_quarenta_leituras_abrem_no_maximo_cinco_conexoes(pool):
    for _ in range(40):
        assert banco.ler_snapshot("ibovespa", date(2026, 10, 29)) == {"valor": 1}
    assert 1 <= pool.conectadas <= 5
    assert pool.devolvidas == 40


def test_close_devolve_ao_pool_sem_fechar(pool):
    conn, backend = banco.get_connection()
    fisica = conn._conn
    conn.close()
    conn.close()  # segundo close não devolve de novo
    assert backend == "postgres"
    assert pool.devolvidas == 1
    assert pool.livres == [fisica]
    fisica.close.assert_not_called()


def test_conexao_esquecida_volta_ao_pool(pool):
    conn, _ = banco.get_connection()
    del conn
    assert pool.devolvidas == 1
    assert not pool.emprestadas


def test_desligamento_do_app_fecha_o_pool(pool):
    from app.main import app

    with TestClient(app):
        assert banco._pool is pool
    assert pool.fechado
    assert banco._pool is None


def test_init_db_do_consultor_devolve_conexao_quando_falha(pool, monkeypatch):
    from app.consultor import armazenamento

    monkeypatch.setattr(armazenamento, "get_connection", banco.get_connection)
    monkeypatch.setattr(armazenamento, "_consultor_db_initialized", False)
    original = pool._conectar

    def conectar_com_erro():
        conn = original()
        conn.cursor.return_value.__enter__.return_value.execute.side_effect = (
            RuntimeError("falhou")
        )
        return conn

    pool._conectar = conectar_com_erro
    armazenamento.init_db()
    assert not pool.emprestadas


def test_diagnostico_traz_o_custo_de_abrir_conexao(pool):
    banco._diagnostico_cache = None
    cursor_fetch = [(9,), (7_800_000,)]
    banco.get_connection()[0].close()
    pool.livres[
        0
    ].cursor.return_value.__enter__.return_value.fetchone.side_effect = cursor_fetch
    pool.livres[0].info.server_version = 170006
    info = banco.diagnostico()
    banco._diagnostico_cache = None
    assert info["versao"] == "17.6"
    assert info["conexao_ms"] == 40


def test_conexao_lenta_vira_atencao_com_a_acao():
    item = verificar_banco(
        {
            "tipo": "Postgres",
            "versao": "17.6",
            "tamanho": "7,8 MB",
            "latencia_ms": 1634,
            "tabelas": 9,
        }
    )
    assert item.nivel == ATENCAO
    assert item.resumo == "Postgres 17.6 · 7,8 MB · 1634 ms"
    assert "endereço interno" in item.detalhe
    assert "endereço interno" in item.acao


def test_conexao_rapida_pelo_pool_fica_ok():
    item = verificar_banco(
        {
            "tipo": "Postgres",
            "tamanho": "7,8 MB",
            "latencia_ms": 4,
            "conexao_ms": 35,
            "tabelas": 9,
        }
    )
    assert item.nivel == OK
    assert "abrir conexão: 35 ms" in item.detalhe
