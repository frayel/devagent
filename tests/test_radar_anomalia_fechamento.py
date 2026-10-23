from app.collectors.radar_anomalia_fechamento import collect_and_save
from app.database import get_latest_radar_anomalia_fechamento_data
from app.services.radar_anomalia_fechamento import get_radar_anomalia_fechamento_view
import json


def test_radar_anomalia_fechamento_sucesso(monkeypatch):
    def mock_get(url, *args, **kwargs):
        class MockResponse:
            def raise_for_status(self):
                pass

            def json(self):
                return {
                    "chart": {
                        "result": [
                            {
                                "meta": {"symbol": "PETR4.SA"},
                                "timestamp": [1, 2],
                                "indicators": {
                                    "quote": [
                                        {"close": [10.0, 10.5], "volume": [100, 200]}
                                    ]
                                },
                            }
                        ]
                    }
                }

        return MockResponse()

    import httpx

    monkeypatch.setattr(httpx.Client, "get", mock_get)

    assert collect_and_save() is True

    data = get_latest_radar_anomalia_fechamento_data()
    assert data is not None
    assert data.fonte == "yfinance"

    alertas = json.loads(data.alertas_json)
    assert len(alertas) > 0
    assert alertas[0]["ticker"] == "PETR4"

    view = get_radar_anomalia_fechamento_view()
    assert view["fonte"] == "yfinance"
    assert len(view["alertas"]) > 0


def test_radar_anomalia_fechamento_vazio():
    from app.banco import get_connection as get_banco_connection

    conn, _ = get_banco_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM snapshots_paineis WHERE painel = 'radar_anomalia_fechamento'"
    )
    conn.commit()
    conn.close()
    view = get_radar_anomalia_fechamento_view()
    assert view == {}
