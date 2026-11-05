import json
from app.collectors.consultor_fechamento import collect_and_save
from app.consultor.armazenamento import get_recomendacoes, init_db, get_connection


def test_consenso_salvo_como_json(monkeypatch):
    # Setup
    init_db()
    conn, _ = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM consultor_recomendacoes")
    conn.commit()

    # Mock calcular_consultor to return known data
    def mock_calcular_consultor(ignorar_cache=False):
        return {
            "resultados": {
                "Comprar": [
                    {
                        "ticker": "TEST1",
                        "timestamp": "2023-01-01 10:00:00 BRT",
                        "regra": "R3 Esticada",
                        "consenso": {"compra": 3, "venda": 1},
                        "fechamento": 10.5,
                        "gatilho": "xyz",
                    }
                ],
                "Vender": [
                    {
                        "ticker": "TEST2",
                        "timestamp": "2023-01-01 10:00:00 BRT",
                        "regra": "R2 Tendência",
                        "consenso": "cobertura insuficiente",
                        "fechamento": 20.0,
                        "gatilho": "abc",
                    }
                ],
            }
        }

    import app.collectors.consultor_fechamento as cf

    monkeypatch.setattr(cf, "calcular_consultor", mock_calcular_consultor)

    # Executa a coleta
    collect_and_save()

    # Retrieve and check
    saved_items = get_recomendacoes("2023-01-01")
    assert len(saved_items) == 2

    for item in saved_items:
        # json.loads deve funcionar
        parsed = json.loads(item["consenso"])
        if item["ticker"] == "TEST1":
            assert parsed == {"compra": 3, "venda": 1}
        elif item["ticker"] == "TEST2":
            assert parsed == "cobertura insuficiente"
