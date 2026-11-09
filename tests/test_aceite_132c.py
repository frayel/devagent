import json
from fastapi.testclient import TestClient

from app.consultor.armazenamento import (
    get_connection,
    init_db,
    migrar_consenso_para_json,
    reset_db_init,
)
from app.main import app

client = TestClient(app)


def test_linha_antiga_processada_e_gravada_como_json():
    # Garante banco inicializado e limpo
    reset_db_init()
    init_db()

    conn, backend = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM consultor_recomendacoes")

    # 1. Linha legada com repr de dict
    c.execute(
        "INSERT INTO consultor_recomendacoes (timestamp, ticker, decisao_final, regra_tecnica, consenso, preco, gatilho) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            "2026-11-09 10:00:00 BRT",
            "PETR4",
            "Comprar",
            "R1",
            "{'compra': 3}",
            35.5,
            "teste",
        ),
    )
    # 2. Linha já em JSON válido
    c.execute(
        "INSERT INTO consultor_recomendacoes (timestamp, ticker, decisao_final, regra_tecnica, consenso, preco, gatilho) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            "2026-11-09 10:00:00 BRT",
            "VALE3",
            "Comprar",
            "R1",
            '{"compra": 5}',
            62.0,
            "teste",
        ),
    )
    # 3. Linha com formato texto simples não-dict
    c.execute(
        "INSERT INTO consultor_recomendacoes (timestamp, ticker, decisao_final, regra_tecnica, consenso, preco, gatilho) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            "2026-11-09 10:00:00 BRT",
            "ITUB4",
            "Aguardar",
            "R2",
            "cobertura insuficiente",
            30.0,
            "teste",
        ),
    )
    conn.commit()
    conn.close()

    # Executa init_db que dispara a migração
    reset_db_init()
    init_db()

    conn, backend = get_connection()
    c = conn.cursor()
    c.execute("SELECT ticker, consenso FROM consultor_recomendacoes ORDER BY ticker")
    rows = dict(c.fetchall())
    conn.close()

    # Linha antiga foi processada e gravada como JSON equivalente
    assert rows["PETR4"] == '{"compra": 3}'
    assert json.loads(rows["PETR4"]) == {"compra": 3}

    # Linha já em JSON foi mantida intacta
    assert rows["VALE3"] == '{"compra": 5}'

    # Linha não-dict foi mantida intacta (invariante de produção)
    assert rows["ITUB4"] == "cobertura insuficiente"


def test_migracao_idempotente():
    reset_db_init()
    init_db()

    conn, backend = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM consultor_recomendacoes")

    c.execute(
        "INSERT INTO consultor_recomendacoes (timestamp, ticker, decisao_final, regra_tecnica, consenso, preco, gatilho) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            "2026-11-09 10:00:00 BRT",
            "BBAS3",
            "Comprar",
            "R1",
            "{'compra': 2, 'venda': 1}",
            28.0,
            "teste",
        ),
    )
    conn.commit()

    # 1ª execução converte a linha
    modificados_1 = migrar_consenso_para_json(conn, backend)
    assert modificados_1 == 1

    # 2ª execução não altera nada
    modificados_2 = migrar_consenso_para_json(conn, backend)
    assert modificados_2 == 0

    c.execute("SELECT consenso FROM consultor_recomendacoes WHERE ticker = 'BBAS3'")
    (consenso,) = c.fetchone()
    conn.close()

    assert consenso == '{"compra": 2, "venda": 1}'


def test_leitura_api_consultor_apos_migracao():
    reset_db_init()
    init_db()

    conn, backend = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM consultor_recomendacoes")

    c.execute(
        "INSERT INTO consultor_recomendacoes (timestamp, ticker, decisao_final, regra_tecnica, consenso, preco, gatilho) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            "2026-11-09 10:00:00 BRT",
            "PETR4",
            "Comprar",
            "R1",
            "{'compra': 4}",
            36.0,
            "teste",
        ),
    )
    conn.commit()
    conn.close()

    # Executa a migração
    reset_db_init()
    init_db()

    # Consulta a API com autenticação básica
    resp = client.get(
        "/api/consultor?data=2026-11-09",
        headers={"Authorization": "Basic Y29uc3VsdG9yOnNlbmhh"},
    )
    # A resposta deve ser 200 ou 404 (se data inválida pelo calendário), não 500
    assert resp.status_code != 500
