"""#1005: o coletor do fechamento grava o ^BVSP em consultor_fechamentos,
senão o "resultado depois do fato" (specs 113b e 131) nunca calcula."""

from datetime import datetime, timezone

from app.collectors import consultor_fechamento
from app.consultor import armazenamento
from app.consultor.armazenamento import get_connection, init_db


class _Depois18h(datetime):
    @classmethod
    def now(cls, tz=None):
        # 20/11/2026 21:30 UTC = 18:30 BRT
        return datetime(2026, 11, 20, 21, 30, tzinfo=timezone.utc)


def _dados(ibov_fechamento):
    item = {
        "ticker": "PETR4.SA",
        "timestamp": "20/11/2026 18:00:00 BRT",
        "regra": "R5 Tendência de alta saudável",
        "consenso": {},
        "fechamento": 38.5,
        "gatilho": "-",
    }
    return {
        "resultados": {
            "Comprar": [item],
            "Vender": [],
            "Aguardar": [],
            "No radar": [],
            "Sem sinal": [],
        },
        "ibov_fechamento": ibov_fechamento,
    }


def _linhas():
    init_db()
    conn, _ = get_connection()
    try:
        c = conn.cursor()
        c.execute(
            "SELECT data_pregao, ticker, preco_fechamento FROM consultor_fechamentos ORDER BY ticker"
        )
        linhas = [tuple(r) for r in c.fetchall()]
        c.execute("SELECT ticker FROM consultor_recomendacoes")
        recs = [r[0] for r in c.fetchall()]
    finally:
        conn.close()
    return linhas, recs


def _limpar():
    init_db()
    conn, _ = get_connection()
    try:
        c = conn.cursor()
        c.execute("DELETE FROM consultor_fechamentos")
        c.execute("DELETE FROM consultor_recomendacoes")
        conn.commit()
    finally:
        conn.close()


def test_coletor_grava_fechamento_do_ibov(monkeypatch):
    _limpar()
    monkeypatch.setattr(armazenamento, "datetime", _Depois18h)
    monkeypatch.setattr(
        consultor_fechamento,
        "calcular_consultor",
        lambda ignorar_cache=False: _dados(127_450.3),
    )

    assert consultor_fechamento.collect_and_save() is True

    linhas, recs = _linhas()
    assert ("2026-11-20", "^BVSP", 127_450.3) in linhas
    assert ("2026-11-20", "PETR4.SA", 38.5) in linhas
    # O índice não vira recomendação.
    assert "^BVSP" not in recs


def test_sem_fechamento_do_ibov_nao_grava_linha_vazia(monkeypatch):
    _limpar()
    monkeypatch.setattr(armazenamento, "datetime", _Depois18h)
    monkeypatch.setattr(
        consultor_fechamento,
        "calcular_consultor",
        lambda ignorar_cache=False: _dados(None),
    )

    assert consultor_fechamento.collect_and_save() is True

    linhas, _ = _linhas()
    assert [t for _, t, _ in linhas] == ["PETR4.SA"]
