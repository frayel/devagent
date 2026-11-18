import json

from app.collectors import scanner_capitulacao


def test_scanner_capitulacao_fallback_simples(monkeypatch):
    class MockClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

        async def get(self, url, **kwargs):
            class MockResponse:
                status_code = 200

                def raise_for_status(self):
                    pass

                def json(self):
                    return {}

            return MockResponse()

    monkeypatch.setattr("httpx.AsyncClient", MockClient)
    monkeypatch.setattr("app.collectors.utils._enforce_rate_limit", lambda d: None)
    assert scanner_capitulacao.collect_and_save() is True

    # Sem série em nenhum ticker, a rodada grava o painel vazio, sem alerta.
    from app.database import get_latest_scanner_capitulacao_data

    gravado = get_latest_scanner_capitulacao_data()
    assert gravado is not None
    assert json.loads(gravado.alertas_json) == []
