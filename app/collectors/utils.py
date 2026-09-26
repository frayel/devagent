import asyncio
import logging
import time
from urllib.parse import urlparse
import httpx

logger = logging.getLogger(__name__)

USER_AGENT = "B3Dashboard/1.0 (+https://github.com/b3-dashboard)"
MIN_DELAY = 2.0  # 2 seconds per domain

# Store the last request time per domain
_last_request_time: dict[str, float] = {}


def _get_domain(url: str) -> str:
    return urlparse(url).netloc


def _enforce_rate_limit(domain: str) -> None:
    now = time.time()
    last_time = _last_request_time.get(domain, 0.0)
    elapsed = now - last_time
    if elapsed < MIN_DELAY:
        sleep_time = MIN_DELAY - elapsed
        logger.debug(f"Rate limiting domain {domain}, sleeping for {sleep_time:.2f}s")
        time.sleep(sleep_time)
    _last_request_time[domain] = time.time()


def fetch_with_retry(
    url: str,
    client: httpx.Client | None = None,
    max_retries: int = 3,
    backoff_factor: float = 1.0,
    **kwargs
) -> httpx.Response:
    domain = _get_domain(url)

    headers = kwargs.get("headers", {})
    if "User-Agent" not in headers:
        headers["User-Agent"] = USER_AGENT
        kwargs["headers"] = headers

    for attempt in range(max_retries):
        _enforce_rate_limit(domain)

        try:
            if client:
                response = client.get(url, **kwargs)
            else:
                response = httpx.get(url, **kwargs)

            # Raise for status to catch 4xx and 5xx errors
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            if status_code == 429 or status_code >= 500:
                if attempt < max_retries - 1:
                    sleep_time = backoff_factor * (2 ** attempt)
                    logger.warning(
                        f"HTTP {status_code} on {url}. Retrying in {sleep_time:.2f}s "
                        f"(attempt {attempt + 1}/{max_retries})"
                    )
                    time.sleep(sleep_time)
                    continue
            raise  # Raise if not retryable or max retries reached
        except httpx.RequestError as e:
            if attempt < max_retries - 1:
                sleep_time = backoff_factor * (2 ** attempt)
                logger.warning(
                    f"Request error {type(e).__name__} on {url}. Retrying in {sleep_time:.2f}s "
                    f"(attempt {attempt + 1}/{max_retries})"
                )
                time.sleep(sleep_time)
                continue
            raise

    raise RuntimeError("Unreachable")
