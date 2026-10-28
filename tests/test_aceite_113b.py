def test_aceite_113b_data_passada(monkeypatch):
    from app.consultor.armazenamento import init_db, get_connection

    init_db()
    conn, _ = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM consultor_recomendacoes")
    c.execute("DELETE FROM consultor_fechamentos")

    c.execute(
        "INSERT INTO consultor_recomendacoes (timestamp, ticker, decisao_final, regra_tecnica, consenso, preco, gatilho) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("2023-10-01 18:00:00 BRT", "TICK1", "Comprar", "R1", "", 10.0, "-"),
    )
    c.execute(
        "INSERT INTO consultor_recomendacoes (timestamp, ticker, decisao_final, regra_tecnica, consenso, preco, gatilho) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("2023-10-02 18:00:00 BRT", "TICK2", "Comprar", "R1", "", 20.0, "-"),
    )

    c.execute(
        "INSERT OR IGNORE INTO consultor_fechamentos (data_pregao, ticker, preco_fechamento) VALUES (?, ?, ?)",
        ("2023-10-01", "TICK1", 10.0),
    )
    c.execute(
        "INSERT OR IGNORE INTO consultor_fechamentos (data_pregao, ticker, preco_fechamento) VALUES (?, ?, ?)",
        ("2023-10-01", "^BVSP", 100.0),
    )
    c.execute(
        "INSERT OR IGNORE INTO consultor_fechamentos (data_pregao, ticker, preco_fechamento) VALUES (?, ?, ?)",
        ("2023-10-02", "TICK1", 12.0),
    )
    c.execute(
        "INSERT OR IGNORE INTO consultor_fechamentos (data_pregao, ticker, preco_fechamento) VALUES (?, ?, ?)",
        ("2023-10-02", "^BVSP", 110.0),
    )
    c.execute(
        "INSERT OR IGNORE INTO consultor_fechamentos (data_pregao, ticker, preco_fechamento) VALUES (?, ?, ?)",
        ("2023-10-02", "TICK2", 20.0),
    )
    conn.commit()

    monkeypatch.setattr(
        "app.main.obter_pregoes_disponiveis",
        lambda a, b, c: ["2023-10-01", "2023-10-02"],
    )
    monkeypatch.setenv("CONSULTOR_SENHA", "senha_secreta")

    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)

    res1 = client.get(
        "/api/consultor?data=2023-10-01", auth=("consultor", "senha_secreta")
    )
    data1 = res1.json()
    msg1 = (
        data1.get("consultor", {})
        .get("resultados", {})
        .get("Comprar", [{}])[0]
        .get("mensagem_confianca", "")
        if "consultor" in data1
        else data1.get("resultados", {})
        .get("Comprar", [{}])[0]
        .get("mensagem_confianca", "")
    )
    assert "em 1 pregões" in msg1

    res2 = client.get(
        "/api/consultor?data=2023-10-02", auth=("consultor", "senha_secreta")
    )
    data2 = res2.json()
    msg2 = (
        data2.get("consultor", {})
        .get("resultados", {})
        .get("Comprar", [{}])[0]
        .get("mensagem_confianca", "")
        if "consultor" in data2
        else data2.get("resultados", {})
        .get("Comprar", [{}])[0]
        .get("mensagem_confianca", "")
    )
    assert msg2 == "ainda sem resultado"
