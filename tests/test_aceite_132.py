import json
from app.consultor import armazenamento
from app.collectors import consultor_fechamento


def test_ler_consenso():
    assert armazenamento.ler_consenso('{"compra": 3}') == {"compra": 3}
    assert (
        armazenamento.ler_consenso('"cobertura insuficiente"')
        == "cobertura insuficiente"
    )
    assert armazenamento.ler_consenso("") == ""

    assert armazenamento.ler_consenso("{'compra': 3}") == {"compra": 3}
    assert (
        armazenamento.ler_consenso("cobertura insuficiente") == "cobertura insuficiente"
    )


def test_migration_idempotent():
    armazenamento.reset_db_init()
    armazenamento.init_db()
    conn, backend = armazenamento.get_connection()
    try:
        c = conn.cursor()
        c.execute("DELETE FROM consultor_recomendacoes WHERE ticker LIKE 'MOCK%'")
        if backend == "postgres":
            c.execute("""
            INSERT INTO consultor_recomendacoes (timestamp, ticker, decisao_final, regra_tecnica, consenso, preco, gatilho)
            VALUES
            ('2026-10-28', 'MOCK1', 'Comprar', 'Regra1', '{"compra": 3}', 10.0, 'g1'),
            ('2026-10-28', 'MOCK2', 'Vender', 'Regra2', 'cobertura insuficiente', 10.0, 'g1'),
            ('2026-10-28', 'MOCK3', 'Aguardar', 'Regra3', '{"compra": 3}', 10.0, 'g1')
            """)
        else:
            c.execute("""
            INSERT INTO consultor_recomendacoes (timestamp, ticker, decisao_final, regra_tecnica, consenso, preco, gatilho)
            VALUES
            ('2026-10-28', 'MOCK1', 'Comprar', 'Regra1', "{'compra': 3}", 10.0, 'g1'),
            ('2026-10-28', 'MOCK2', 'Vender', 'Regra2', 'cobertura insuficiente', 10.0, 'g1'),
            ('2026-10-28', 'MOCK3', 'Aguardar', 'Regra3', '{"compra": 3}', 10.0, 'g1')
            """)
        conn.commit()
    finally:
        conn.close()

    armazenamento.reset_db_init()
    armazenamento.init_db()

    conn, backend = armazenamento.get_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT consenso FROM consultor_recomendacoes WHERE ticker = 'MOCK1'")
        res = c.fetchone()[0]
        assert res == '{"compra": 3}'

        c.execute("SELECT consenso FROM consultor_recomendacoes WHERE ticker = 'MOCK2'")
        res2 = c.fetchone()[0]
        assert res2 == "cobertura insuficiente"

        c.execute("SELECT consenso FROM consultor_recomendacoes WHERE ticker = 'MOCK3'")
        res3 = c.fetchone()[0]
        assert res3 == '{"compra": 3}'
    finally:
        conn.close()

    armazenamento.reset_db_init()
    armazenamento.init_db()

    conn, backend = armazenamento.get_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT consenso FROM consultor_recomendacoes WHERE ticker = 'MOCK1'")
        res = c.fetchone()[0]
        assert res == '{"compra": 3}'
    finally:
        conn.close()


def test_gravar_consenso():
    import datetime
    from unittest.mock import patch

    class MockDatetime(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            from datetime import timezone, timedelta

            return cls(2026, 10, 28, 20, 0, 0, tzinfo=timezone(timedelta(hours=-3)))

    patch("app.consultor.armazenamento.datetime", MockDatetime).start()
    armazenamento.reset_db_init()
    armazenamento.init_db()

    original = consultor_fechamento.calcular_consultor

    def mock_calc(ignorar_cache=False, db_conn=None):
        return {
            "resultados": {
                "Comprar": [
                    {
                        "ticker": "TEST1",
                        "timestamp": "2026-10-28T10:00:00Z",
                        "regra": "r",
                        "consenso": {"compra": 3, "venda": 1},
                        "fechamento": 10.0,
                        "gatilho": "g",
                    }
                ],
                "Aguardar": [
                    {
                        "ticker": "TEST2",
                        "timestamp": "2026-10-28T10:00:00Z",
                        "regra": "r",
                        "consenso": "cobertura insuficiente",
                        "fechamento": 10.0,
                        "gatilho": "g",
                    }
                ],
            }
        }

    consultor_fechamento.calcular_consultor = mock_calc

    try:
        consultor_fechamento.collect_and_save()
    finally:
        consultor_fechamento.calcular_consultor = original

    conn, backend = armazenamento.get_connection()
    try:
        c = conn.cursor()
        c.execute(
            "SELECT consenso FROM consultor_recomendacoes WHERE ticker = 'TEST1' ORDER BY id DESC LIMIT 1"
        )
        res1 = c.fetchone()[0]
        assert json.loads(res1) == {"compra": 3, "venda": 1}

        c.execute(
            "SELECT consenso FROM consultor_recomendacoes WHERE ticker = 'TEST2' ORDER BY id DESC LIMIT 1"
        )
        res2 = c.fetchone()[0]
        assert json.loads(res2) == "cobertura insuficiente"
    finally:
        conn.close()
