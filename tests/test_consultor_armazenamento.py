from app.banco import get_backend_type
from app.consultor.armazenamento import (
    save_recomendacoes,
)
from app.database import get_connection


def test_fallback_sqlite(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    backend = get_backend_type()
    assert backend == "sqlite_efemero"


def test_save_recomendacoes(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    conn = get_connection()
    from app.consultor.armazenamento import init_db

    init_db()
    c = conn.cursor()
    c.execute("DELETE FROM consultor_recomendacoes")
    conn.commit()
    conn.close()

    res = [
        {
            "ticker": "PETR4",
            "timestamp": "2023-01-01 10:00",
            "decisao": "Comprar",
            "regra": "R3 Esticada",
            "consenso": "{}",
            "preco": 10.5,
            "gatilho": "xyz",
        }
    ]
    save_recomendacoes(res)

    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM consultor_recomendacoes")
    count1 = c.fetchone()[0]

    save_recomendacoes(res)  # Should not duplicate
    c.execute("SELECT COUNT(*) FROM consultor_recomendacoes")
    count2 = c.fetchone()[0]
    conn.close()

    assert count1 == 1
    assert count2 == 1
