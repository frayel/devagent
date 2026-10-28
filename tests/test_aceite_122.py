import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from app.banco import diagnostico
from app.database import get_historico_diario, save_historico_diario
from app.consultor.calculador import calcular_consultor


@pytest.fixture(autouse=True)
def clean_caches():
    # Clean up caches
    import app.banco

    app.banco._diagnostico_cache = None
    app.banco._diagnostico_cache_time = None

    app.database._historico_diario_cache = {}

    import app.consultor.calculador

    app.consultor.calculador._consultor_cache = None
    app.consultor.calculador._consultor_cache_versao = None
    app.consultor.calculador._consultor_cache_time = None
    yield
    app.banco._diagnostico_cache = None
    app.database._historico_diario_cache = {}
    app.consultor.calculador._consultor_cache = None


def test_get_historico_diario_data_inicio():
    # 1. get_historico_diario([...], "1d", ...) consulta o banco com data de inicio no max 5 dias corridos
    with patch("app.banco.ler_series") as mock_ler_series:
        mock_ler_series.return_value = {"ITUB4": [{"data": "2023-10-10", "close": 10}]}
        get_historico_diario(["ITUB4"], "1d", "1d")

        # Verify the call to ler_series
        assert mock_ler_series.called
        args, _ = mock_ler_series.call_args
        inicio = args[1]
        hoje = args[2]

        assert inicio == hoje - timedelta(days=5)


def test_get_historico_diario_max_age_minutes():
    # 2. get_historico_diario com max_age_minutes=15 não devolve ticker cuja ultima gravação tem 20 min durante o pregão
    agora = datetime.now(timezone.utc)
    # Mocking mercado_aberto to return True
    with patch("app.calendario.mercado_aberto", return_value=True):
        with patch("app.banco.ler_series") as mock_ler_series:
            # 20 min ago
            criado_em = (agora - timedelta(minutes=20)).isoformat()
            mock_ler_series.return_value = {
                "ITUB4": [{"data": "2023-10-10", "close": 10, "criado_em": criado_em}]
            }
            # Should be empty because it's older than 15 min and mercado is open
            res = get_historico_diario(["ITUB4"], "1d", "1d", max_age_minutes=15)
            assert not res.get("ITUB4")

    # Mocking mercado_aberto to return False
    with patch("app.calendario.mercado_aberto", return_value=False):
        with patch("app.banco.ler_series") as mock_ler_series:
            criado_em = (agora - timedelta(minutes=20)).isoformat()
            mock_ler_series.return_value = {
                "ITUB4": [{"data": "2023-10-10", "close": 10, "criado_em": criado_em}]
            }
            # Should return data because mercado is closed
            res = get_historico_diario(["ITUB4"], "1d", "1d", max_age_minutes=15)
            assert res.get("ITUB4")


def test_calcular_consultor_cache_chamadas():
    # 3. Duas chamadas a calcular_consultor sem gravação nova geram unica leitura
    with patch("app.consultor.calculador.get_historico_diario") as mock_get_hist:
        mock_get_hist.return_value = {"^BVSP": {"symbol": "^BVSP", "timestamp": [1]}}
        with patch("app.banco.versao_series", return_value="v1"):
            calcular_consultor()
            assert mock_get_hist.call_count == 1

            calcular_consultor()
            # Still 1, didn't call again
            assert mock_get_hist.call_count == 1

        with patch("app.banco.versao_series", return_value="v2"):
            calcular_consultor()
            # Now called again because versao changed
            assert mock_get_hist.call_count == 2


def test_historico_diario_cache_chamadas():
    # 4. Duas chamadas a get_historico_diario sem gravacao geram uma consulta.
    # Após save_historico_diario, a terceira gera consulta.
    with patch("app.banco.ler_series") as mock_ler_series:
        mock_ler_series.return_value = {"BBDC4": [{"data": "2023-10-10", "close": 10}]}
        get_historico_diario(["BBDC4"], "1d", "1d")
        assert mock_ler_series.call_count == 1

        get_historico_diario(["BBDC4"], "1d", "1d")
        assert mock_ler_series.call_count == 1

        # Save
        with patch("app.banco.gravar_serie"):
            save_historico_diario(
                "BBDC4",
                "1d",
                "1d",
                '{"timestamp":[1696950000],"indicators":{"quote":[{"close":[15]}]}}',
                datetime.now(),
            )

        # Third call
        get_historico_diario(["BBDC4"], "1d", "1d")
        assert mock_ler_series.call_count == 2


def test_diagnostico_cache():
    # 5. Duas chamadas a diagnostico() em menos de 5 min geram uma consulta (latencia muda apenas na 1a)
    with patch("app.banco.get_backend_type", return_value="sqlite_efemero"):
        with patch("os.path.getsize", return_value=1024):
            d1 = diagnostico()
            d2 = diagnostico()
            assert d1 is d2
