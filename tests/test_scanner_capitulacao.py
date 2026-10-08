from app.collectors import scanner_capitulacao


def test_scanner_capitulacao_fallback_simples(monkeypatch):
    class MockClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

        async def get(self, url, timeout=10.0):
            class MockResponse:
                def raise_for_status(self):
                    pass

                def json(self):
                    return {}

            return MockResponse()

    monkeypatch.setattr("httpx.AsyncClient", MockClient)
    scanner_capitulacao.collect_and_save()
