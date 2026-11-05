from datetime import datetime, timedelta
from app.consultor.armazenamento import init_db, get_connection


def test_aceite_131_historico_sem_n1(monkeypatch):
    init_db()
    conn, _ = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM consultor_recomendacoes")
    c.execute("DELETE FROM consultor_fechamentos")

    # Gerar 85 recomendações para o dia D ("2023-11-01")
    tickers = [f"TICK{i}" for i in range(1, 86)]
    for ticker in tickers:
        c.execute(
            "INSERT INTO consultor_recomendacoes (timestamp, ticker, decisao_final, regra_tecnica, consenso, preco, gatilho) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("2023-11-01 18:00:00 BRT", ticker, "Comprar", "R1", "", 10.0, "-"),
        )

    # Gerar 10 pregões de fechamento (D até D+9)
    # D = 2023-11-01
    datas_pregao = []
    base_date = datetime(2023, 11, 1)
    for i in range(10):
        dp = (base_date + timedelta(days=i)).strftime("%Y-%m-%d")
        datas_pregao.append(dp)

        c.execute(
            "INSERT OR IGNORE INTO consultor_fechamentos (data_pregao, ticker, preco_fechamento) VALUES (?, ?, ?)",
            (dp, "^BVSP", 100.0 * (1 + i * 0.01)),  # IBOV sobe 1% ao dia
        )
        for ticker in tickers:
            c.execute(
                "INSERT OR IGNORE INTO consultor_fechamentos (data_pregao, ticker, preco_fechamento) VALUES (?, ?, ?)",
                (dp, ticker, 10.0 * (1 + i * 0.02)),  # Ativos sobem 2% ao dia
            )

    conn.commit()

    monkeypatch.setenv("CONSULTOR_SENHA", "senha_secreta")
    import app.main

    monkeypatch.setattr(
        app.main, "obter_pregoes_disponiveis", lambda a, b, c: datas_pregao
    )

    # Spy connections
    from app.consultor import armazenamento

    original_get_connection = armazenamento.get_connection

    connections_opened = 0

    def spy_get_connection():
        nonlocal connections_opened
        connections_opened += 1
        return original_get_connection()

    monkeypatch.setattr(
        "app.consultor.armazenamento.get_connection", spy_get_connection
    )

    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)

    res = client.get(
        "/api/consultor?data=2023-11-01", auth=("consultor", "senha_secreta")
    )
    assert res.status_code == 200

    data = res.json()
    resultados = data.get("resultados", {})
    if "consultor" in data:
        resultados = data["consultor"].get("resultados", {})

    compras = resultados.get("Comprar", [])
    assert len(compras) == 85

    for item in compras:
        assert item["mensagem_confianca"] == "+5.0% contra o IBOV em 5 pregões"

    assert connections_opened <= 8
