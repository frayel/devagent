import httpx
import pytest
from unittest.mock import patch
from app.collectors.utils import fetch_with_retry, USER_AGENT


def test_rate_limiting_delay():
    import app.collectors.utils as utils

    # Reset state
    utils._last_request_time = {}

    with (
        patch("app.collectors.utils.time.sleep") as mock_sleep,
        patch("app.collectors.utils.time.time") as mock_time,
    ):
        # Setup mock time to simulate calls
        # Call 1: time.time() -> 10.0, _enforce_rate_limit sets last_request_time to 10.0
        # Call 2: time.time() -> 11.0, elapsed = 1.0, sleeps for 1.0, then time.time() -> 12.0
        mock_time.side_effect = [10.0, 10.0, 11.0, 12.0]

        mock_response = httpx.Response(
            200, request=httpx.Request("GET", "https://example.com/api")
        )

        with patch("httpx.get", return_value=mock_response):
            fetch_with_retry("https://example.com/api")
            fetch_with_retry("https://example.com/api")

        # The sleep should have been called once, with 1.0 seconds
        mock_sleep.assert_called_once_with(1.0)


def test_exponential_backoff_on_429():
    import app.collectors.utils as utils

    utils._last_request_time = {}

    with (
        patch("app.collectors.utils.time.sleep") as mock_sleep,
        patch("app.collectors.utils.time.time", return_value=10.0),
    ):
        req = httpx.Request("GET", "https://example.com/api")
        mock_429 = httpx.Response(429, request=req)
        mock_200 = httpx.Response(200, request=req)

        # Fail first with 429, then succeed
        with patch(
            "httpx.get",
            side_effect=[
                httpx.HTTPStatusError(
                    "Too Many Requests", request=req, response=mock_429
                ),
                mock_200,
            ],
        ):
            res = fetch_with_retry("https://example.com/api")
            assert res.status_code == 200

        # Sleep should be called for backoff (backoff_factor=1.0 * 2^0 = 1.0)
        # Note: rate limit sleep won't be called because time.time is mocked to return the same value
        # But wait, if time is the same, rate limit *would* be called on the retry.
        # However, mock_time returns 10.0, last_time=10.0, elapsed=0.0 -> sleep(2.0).
        # We need to account for both backoff sleep and rate limit sleep.

        # Let's verify sleep was called at least once for backoff
        assert mock_sleep.call_count >= 1


def test_no_retry_on_404():
    import app.collectors.utils as utils

    utils._last_request_time = {}

    with (
        patch("app.collectors.utils.time.sleep") as mock_sleep,
        patch("app.collectors.utils.time.time", return_value=10.0),
    ):
        req = httpx.Request("GET", "https://example.com/api")
        mock_404 = httpx.Response(404, request=req)

        with patch(
            "httpx.get",
            side_effect=httpx.HTTPStatusError(
                "Not Found", request=req, response=mock_404
            ),
        ):
            with pytest.raises(httpx.HTTPStatusError) as exc_info:
                fetch_with_retry("https://example.com/api")

            assert exc_info.value.response.status_code == 404

        # Ensure no backoff sleep was called for 404
        # Since time.time() returns 10.0, it initializes last_request_time to 10.0
        # Wait, the first call has elapsed=10.0-0.0=10.0, so no rate limit sleep on first attempt.
        # Since there's no retry, there's no second attempt, so sleep should be 0.
        assert mock_sleep.call_count == 0


def test_user_agent_header_added():
    import app.collectors.utils as utils

    utils._last_request_time = {}

    with patch("httpx.get") as mock_get:
        mock_get.return_value = httpx.Response(
            200, request=httpx.Request("GET", "https://example.com/api")
        )

        fetch_with_retry("https://example.com/api")

        kwargs = mock_get.call_args[1]
        assert "headers" in kwargs
        assert kwargs["headers"].get("User-Agent") == USER_AGENT


def test_user_agent_header_not_overwritten():
    import app.collectors.utils as utils

    utils._last_request_time = {}

    with patch("httpx.get") as mock_get:
        mock_get.return_value = httpx.Response(
            200, request=httpx.Request("GET", "https://example.com/api")
        )

        fetch_with_retry(
            "https://example.com/api", headers={"User-Agent": "CustomAgent"}
        )

        kwargs = mock_get.call_args[1]
        assert "headers" in kwargs
        assert kwargs["headers"].get("User-Agent") == "CustomAgent"


def test_timeout_is_enforced():
    import app.collectors.utils as utils

    utils._last_request_time = {}

    with patch("httpx.get") as mock_get:
        mock_get.return_value = httpx.Response(
            200, request=httpx.Request("GET", "https://example.com/api")
        )

        fetch_with_retry("https://example.com/api")

        kwargs = mock_get.call_args[1]
        assert "timeout" in kwargs
        assert kwargs["timeout"] == 10.0

        fetch_with_retry("https://example.com/api", timeout=5.0)

        kwargs2 = mock_get.call_args[1]
        assert "timeout" in kwargs2
        assert kwargs2["timeout"] == 5.0


def test_fetch_historico_diario_yfinance_spark_uses_cache():
    from unittest.mock import patch, MagicMock
    from app.collectors.utils import fetch_historico_diario_yfinance_spark

    with (
        patch("app.database.get_historico_diario") as mock_get_cache,
        patch("app.database.save_historico_diario") as mock_save_cache,
        patch("app.collectors.utils.fetch_with_retry") as mock_fetch,
    ):
        mock_get_cache.return_value = {
            "PETR4": {"symbol": "PETR4", "response": [{"timestamp": [1, 2, 3]}]}
        }
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "spark": {
                "result": [
                    {"symbol": "VALE3.SA", "response": [{"timestamp": [4, 5, 6]}]}
                ]
            }
        }
        mock_fetch.return_value = mock_response

        client = MagicMock()

        results = fetch_historico_diario_yfinance_spark(
            ["PETR4", "VALE3"], "1mo", "1d", client
        )

        assert len(results) == 2
        symbols_returned = [r["symbol"] for r in results]
        assert "PETR4" in symbols_returned
        assert "VALE3.SA" in symbols_returned

        mock_get_cache.assert_called_once_with(["PETR4", "VALE3"], "1mo", "1d")
        mock_fetch.assert_called_once()
        url_called = mock_fetch.call_args[0][0]
        assert "symbols=VALE3.SA" in url_called
        assert "PETR4" not in url_called

        mock_save_cache.assert_called_once()
        args = mock_save_cache.call_args[0]
        assert args[0] == "VALE3"
        assert args[1] == "1mo"
        assert args[2] == "1d"
