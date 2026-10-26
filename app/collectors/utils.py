import logging
import asyncio
import time
import re
from urllib.parse import urlparse
import httpx

from app.collectors import registro_fontes

logger = logging.getLogger(__name__)

# Identificável (seção 5 do PRODUTO.md) e com prefixo "Mozilla/5.0 (compatible; ...)",
# o formato dos robôs conhecidos: o Yahoo Finance recusa User-Agents fora dele.
USER_AGENT = (
    "Mozilla/5.0 (compatible; B3Dashboard/1.0; +https://github.com/frayel/devagent)"
)
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


_request_counter: int = 0


def fetch_with_retry(
    url: str,
    client: httpx.Client | None = None,
    max_retries: int = 3,
    backoff_factor: float = 1.0,
    **kwargs,
) -> httpx.Response:
    global _request_counter
    if "query1.finance.yahoo.com" in url:
        if _request_counter % 2 == 1:
            url = url.replace("query1.finance.yahoo.com", "query2.finance.yahoo.com")
        _request_counter += 1
    # O MetaTrader 5 é a fonte preferencial das URLs do Yahoo Finance: se ele
    # responder, o Yahoo nem é chamado (app/collectors/mt5.py).
    from app.collectors import mt5

    resposta_mt5 = mt5.interceptar(url)
    if resposta_mt5 is not None:
        return resposta_mt5

    domain = _get_domain(url)
    if "finance.yahoo.com" in domain:
        mt5.registrar_fonte(mt5.FONTE_YAHOO)

    headers = kwargs.get("headers", {})
    if "User-Agent" not in headers:
        headers["User-Agent"] = USER_AGENT
        kwargs["headers"] = headers

    if "timeout" not in kwargs:
        kwargs["timeout"] = 10.0

    for attempt in range(max_retries):
        _enforce_rate_limit(domain)

        try:
            if client:
                response = client.get(url, **kwargs)
            else:
                response = httpx.get(url, **kwargs)

            # Raise for status to catch 4xx and 5xx errors
            if response.status_code >= 400:
                response.raise_for_status()

            if response.status_code < 400:
                registro_fontes.sucesso(registro_fontes.nome_da_fonte(domain), url=url)
            return response
        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            if status_code == 429 or status_code >= 500:
                if attempt < max_retries - 1:
                    sleep_time = backoff_factor * (2**attempt)
                    safe_url = re.sub(r"([?&]token=)[^&\s]+", r"\1***", url)
                    logger.warning(
                        f"HTTP {status_code} on {safe_url}. Retrying in {sleep_time:.2f}s "
                        f"(attempt {attempt + 1}/{max_retries})"
                    )
                    time.sleep(sleep_time)
                    continue
            corpo = (
                e.response.text
                if hasattr(e, "response") and hasattr(e.response, "text")
                else None
            )
            registro_fontes.falha(
                registro_fontes.nome_da_fonte(domain),
                f"HTTP {status_code} em {url}",
                grave=registro_fontes.grave(status_code),
                url=url,
                corpo=corpo,
                status=status_code,
            )
            raise  # Raise if not retryable or max retries reached
        except httpx.RequestError as e:
            if attempt < max_retries - 1:
                sleep_time = backoff_factor * (2**attempt)
                safe_url = re.sub(r"([?&]token=)[^&\s]+", r"\1***", url)
                logger.warning(
                    f"Request error {type(e).__name__} on {safe_url}. Retrying in {sleep_time:.2f}s "
                    f"(attempt {attempt + 1}/{max_retries})"
                )
                time.sleep(sleep_time)
                continue
            registro_fontes.falha(
                registro_fontes.nome_da_fonte(domain),
                f"{type(e).__name__} em {url}",
                url=url,
            )
            raise

    raise RuntimeError("Unreachable")


async def async_fetch_with_retry(
    url: str,
    client: httpx.AsyncClient,
    max_retries: int = 3,
    backoff_factor: float = 1.0,
    **kwargs,
) -> httpx.Response:
    global _request_counter
    if "query1.finance.yahoo.com" in url:
        if _request_counter % 2 == 1:
            url = url.replace("query1.finance.yahoo.com", "query2.finance.yahoo.com")
        _request_counter += 1
    from app.collectors import mt5

    resposta_mt5 = mt5.interceptar(url)
    if resposta_mt5 is not None:
        return resposta_mt5

    domain = _get_domain(url)
    if "finance.yahoo.com" in domain:
        mt5.registrar_fonte(mt5.FONTE_YAHOO)

    headers = kwargs.get("headers", {})
    if "User-Agent" not in headers:
        headers["User-Agent"] = USER_AGENT
    kwargs["headers"] = headers

    for attempt in range(max_retries):
        try:
            _enforce_rate_limit(domain)
            response = await client.get(url, **kwargs)
            status_code = response.status_code
            if status_code == 429 or status_code >= 500:
                safe_url = re.sub(r"([?&]token=)[^&\s]+", r"\1***", url)
                logger.warning(
                    f"Attempt {attempt + 1} failed for {safe_url} with status {status_code}"
                )
                if attempt < max_retries - 1:
                    sleep_time = backoff_factor * (2**attempt)
                    logger.info(f"Retrying in {sleep_time} seconds...")
                    await asyncio.sleep(sleep_time)
                    continue
                corpo = response.text if hasattr(response, "text") else None
                registro_fontes.falha(
                    registro_fontes.nome_da_fonte(domain),
                    f"HTTP {status_code} em {url}",
                    url=url,
                    corpo=corpo,
                    status=status_code,
                )
                response.raise_for_status()

            if status_code < 400:
                registro_fontes.sucesso(registro_fontes.nome_da_fonte(domain), url=url)
            else:
                corpo = response.text if hasattr(response, "text") else None
                registro_fontes.falha(
                    registro_fontes.nome_da_fonte(domain),
                    f"HTTP {status_code} em {url}",
                    grave=registro_fontes.grave(status_code),
                    url=url,
                    corpo=corpo,
                    status=status_code,
                )
            return response

        except httpx.RequestError as e:
            safe_url = re.sub(r"([?&]token=)[^&\s]+", r"\1***", url)
            logger.warning(
                f"Attempt {attempt + 1} failed for {safe_url} with error {e}"
            )
            if attempt < max_retries - 1:
                sleep_time = backoff_factor * (2**attempt)
                logger.info(f"Retrying in {sleep_time} seconds...")
                await asyncio.sleep(sleep_time)
                continue
            registro_fontes.falha(
                registro_fontes.nome_da_fonte(domain),
                f"{type(e).__name__} em {url}",
                url=url,
            )
            raise

    safe_url = re.sub(r"([?&]token=)[^&\s]+", r"\1***", url)
    raise Exception(f"Failed to fetch {safe_url} after {max_retries} attempts")


def fetch_historico_diario_yfinance_spark(
    symbols: list[str], range_str: str, interval: str, client: httpx.Client
) -> list[dict]:
    import json
    from datetime import datetime, timezone

    from app.database import get_historico_diario, save_historico_diario
    from app.database import registrar_falha_simbolo, is_simbolo_suspenso

    # Filtrar suspensos
    valid_symbols = [s for s in symbols if not is_simbolo_suspenso("yfinance", s)]

    # 1. Check cache
    cached_data = get_historico_diario(valid_symbols, range_str, interval)
    missing_symbols = [s for s in valid_symbols if s not in cached_data]

    all_results = []

    # Add cached data
    for ticker, data in cached_data.items():
        all_results.append(data)

    if not missing_symbols:
        return all_results

    # 2. Fetch missing data in batches
    agora = datetime.now(timezone.utc)

    queue = []
    batch_size = 15
    for i in range(0, len(missing_symbols), batch_size):
        queue.append((missing_symbols[i : i + batch_size], 4))

    while queue:
        batch, max_divisoes = queue.pop(0)
        if not batch:
            continue

        batch_query = ",".join(
            [
                simbolo_yahoo(t.replace(".SA", ""))
                if not t.endswith(".SA") and not t.startswith("^") and "=" not in t
                else t
                for t in batch
            ]
        )
        url = f"https://query1.finance.yahoo.com/v7/finance/spark?symbols={batch_query}&range={range_str}&interval={interval}"

        try:
            response = fetch_with_retry(url, client=client)
            data = response.json()

            for item in data.get("spark", {}).get("result", []):
                if not item:
                    continue
                symbol = item.get("symbol", "").replace(".SA", "")

                registrar_falha_simbolo("yfinance", symbol, sucesso=True)

                save_historico_diario(
                    symbol, range_str, interval, json.dumps(item), agora
                )

                all_results.append(item)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                if len(batch) > 1 and max_divisoes > 0:
                    mid = len(batch) // 2
                    queue.append((batch[:mid], max_divisoes - 1))
                    queue.append((batch[mid:], max_divisoes - 1))
                elif len(batch) == 1:
                    bad_symbol = batch[0].replace(".SA", "")
                    registrar_falha_simbolo("yfinance", bad_symbol, sucesso=False)
                    logger.warning(f"Symbol {bad_symbol} returned 404, isolated.")
            else:
                logger.error(f"Error fetching batch {batch_query} from yfinance: {e}")
        except httpx.HTTPError as e:
            logger.error(f"Error fetching batch {batch_query} from yfinance: {e}")

    return all_results


def simbolo_yahoo(symbol: str) -> str:
    """Ticker da B3 ganha `.SA`; índices (`^BVSP`) e câmbio (`BRL=X`) não."""
    if symbol.startswith("^") or "=" in symbol or "." in symbol:
        return symbol
    return f"{symbol}.SA"


def fetch_historico_diario_yfinance_chart(
    symbol: str,
    range_str: str,
    interval: str,
    client: httpx.Client,
    max_age_minutes: int = 15,
) -> dict | None:
    import json
    from datetime import datetime, timezone
    from app.database import get_historico_diario, save_historico_diario
    from app.database import registrar_falha_simbolo, is_simbolo_suspenso

    if is_simbolo_suspenso("yfinance", symbol):
        return None

    cached_data = get_historico_diario(
        [symbol], range_str, interval, max_age_minutes=max_age_minutes
    )
    if symbol in cached_data:
        return cached_data[symbol]

    url = f"https://query2.finance.yahoo.com/v8/finance/chart/{simbolo_yahoo(symbol)}?range={range_str}&interval={interval}"
    try:
        response = fetch_with_retry(url, client=client)
        registrar_falha_simbolo("yfinance", symbol, sucesso=True)
        data = response.json()
        result = data.get("chart", {}).get("result", [])
        if not result:
            return None

        item = result[0]

        spark_like_item = {
            "symbol": symbol,
            "timestamp": item.get("timestamp", []),
            "indicators": {
                "quote": [
                    {
                        "close": item.get("indicators", {})
                        .get("quote", [{}])[0]
                        .get("close", []),
                        "volume": item.get("indicators", {})
                        .get("quote", [{}])[0]
                        .get("volume", []),
                        "open": item.get("indicators", {})
                        .get("quote", [{}])[0]
                        .get("open", []),
                        "high": item.get("indicators", {})
                        .get("quote", [{}])[0]
                        .get("high", []),
                        "low": item.get("indicators", {})
                        .get("quote", [{}])[0]
                        .get("low", []),
                    }
                ]
            },
        }

        agora = datetime.now(timezone.utc)
        save_historico_diario(
            symbol, range_str, interval, json.dumps(spark_like_item), agora
        )
        return spark_like_item
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            registrar_falha_simbolo("yfinance", symbol, sucesso=False)
            logger.warning(f"Symbol {symbol} returned 404, isolated.")
        else:
            logger.error(f"Error fetching chart {symbol} from yfinance: {e}")
        return None
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            registrar_falha_simbolo("yfinance", symbol, sucesso=False)
            logger.warning(f"Symbol {symbol} returned 404, isolated.")
        else:
            logger.error(f"Error fetching chart {symbol} from yfinance: {e}")
        return None
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            registrar_falha_simbolo("yfinance", symbol, sucesso=False)
            logger.warning(f"Symbol {symbol} returned 404, isolated.")
        else:
            logger.error(f"Error fetching chart {symbol} from yfinance: {e}")
        return None
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            registrar_falha_simbolo("yfinance", symbol, sucesso=False)
            logger.warning(f"Symbol {symbol} returned 404, isolated.")
        else:
            logger.error(f"Error fetching chart {symbol} from yfinance: {e}")
        return None
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            registrar_falha_simbolo("yfinance", symbol, sucesso=False)
            logger.warning(f"Symbol {symbol} returned 404, isolated.")
        else:
            logger.error(f"Error fetching chart {symbol} from yfinance: {e}")
        return None
    except httpx.HTTPError as e:
        logger.error(f"Error fetching chart {symbol} from yfinance: {e}")
        return None
