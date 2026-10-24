from fastapi.testclient import TestClient


def test_api_diagnostico(monkeypatch):
    monkeypatch.setenv("CONSULTOR_SENHA", "123")

    # Mocking functions for API payload
    from app.main import app

    client = TestClient(app)

    # In a clean DB, it should be 'aguardando'
    from app.consultor.armazenamento import get_connection, init_db

    init_db()
    conn, b = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM consultor_opinioes_status")
    c.execute("DELETE FROM consultor_opinioes")
    c.execute("DELETE FROM consultor_fila_materias")
    conn.commit()
    conn.close()

    resp = client.get(
        "/api/consultor", headers={"Authorization": "Basic Y29uc3VsdG9yOjEyMw=="}
    )  # Base64 for consultor:123
    assert resp.status_code == 200
    data = resp.json()

    diag = data["fontes_opiniao"]["diagnostico"]
    assert diag["codigo"] == "aguardando"


def test_consultor_html_casos(monkeypatch):
    monkeypatch.setenv("CONSULTOR_SENHA", "123")
    from app.main import app

    client = TestClient(app)

    from app.consultor.armazenamento import get_connection, init_db

    init_db()

    def set_status(
        status, motivo="", ultima_extracao="", mat_proc=0, op_grav=0, descartadas=0
    ):
        conn, b = get_connection()
        c = conn.cursor()
        c.execute("DELETE FROM consultor_opinioes_status")
        c.execute(
            "INSERT INTO consultor_opinioes_status (status, motivo, desde, ultima_extracao_em, materias_processadas, opinioes_gravadas, descartadas) VALUES (?, ?, '2026-01-01T12:00:00Z', ?, ?, ?, ?)",
            (status, motivo, ultima_extracao, mat_proc, op_grav, descartadas),
        )
        c.execute("DELETE FROM consultor_fila_materias")
        conn.commit()
        conn.close()

    def get_html():
        resp = client.get(
            "/consultor", headers={"Authorization": "Basic Y29uc3VsdG9yOjEyMw=="}
        )
        assert resp.status_code == 200
        return resp.text

    # Caso 1: sem_chave
    set_status("sem_chave", "sem chave configurada")
    html = get_html()
    assert "Extração desligada: falta a chave do Gemini." in html
    assert "Nenhuma opinião recente." not in html

    # Caso 2: cota
    set_status("cota")
    html = get_html()
    assert "Cota diária do Gemini esgotada (0 chamadas). Volta amanhã." in html

    # Caso 3: erro
    set_status("erro", "LLM timeout")
    html = get_html()
    assert "A última extração falhou às 12:00 (LLM timeout)." in html

    # Caso 4: aguardando
    conn, b = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM consultor_opinioes_status")
    c.execute(
        "INSERT INTO consultor_opinioes_status (status, desde) VALUES ('ok', '2026-01-01T12:00:00Z')"
    )
    c.execute(
        "INSERT INTO consultor_fila_materias (guid, titulo, descricao, conteudo, link, tickers_citados, data_publicacao, criado_em) VALUES ('g1', 'T', 'D', 'C', 'L', '[]', '2026-01-01', '2026-01-01T12:00:00')"
    )
    c.execute(
        "INSERT INTO consultor_fila_materias (guid, titulo, descricao, conteudo, link, tickers_citados, data_publicacao, criado_em) VALUES ('g2', 'T', 'D', 'C', 'L', '[]', '2026-01-01', '2026-01-01T12:00:00')"
    )
    conn.commit()
    conn.close()

    html = get_html()
    assert "Aguardando a primeira extração. Há 2 matérias na fila." in html

    # Caso 5: fila (já teve extracao)
    set_status("ok", ultima_extracao="24/10 12:00 BRT")
    conn, b = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO consultor_fila_materias (guid, titulo, descricao, conteudo, link, tickers_citados, data_publicacao, criado_em) VALUES ('g3', 'T', 'D', 'C', 'L', '[]', '2026-01-01', '2026-01-01T12:00:00')"
    )
    conn.commit()
    conn.close()

    html = get_html()
    assert "1 matérias na fila, a próxima extração é na próxima rodada." in html

    # Caso 6: sem materias
    set_status("ok", ultima_extracao="24/10 12:00 BRT")
    conn, b = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM consultor_fila_materias")
    conn.commit()
    conn.close()

    html = get_html()
    assert (
        "Nenhuma matéria dos feeds citou ativos do Ibovespa com opinião de casa de análise nos últimos 30 dias."
        in html
    )

    # Caso 7: descartadas
    set_status("ok", ultima_extracao="24/10 12:00 BRT", descartadas=3)
    html = get_html()
    assert (
        "3 opiniões extraídas foram descartadas porque o trecho citado não está na matéria."
        in html
    )
