---
gaveta: saúde técnica
---

# Spec 054: Refatoração do Scanner de Capitulação

## Problema

O `scanner_capitulacao` fazia 30 requisições sequenciais usando `httpx.get` e o `fetch_with_retry` síncrono para o endpoint `v8/finance/chart/{ticker}.SA` do Yahoo Finance, pois precisa de OHLCV intraday. Como isso acontece em cada inicialização do serviço (em `app.agendador._coletar`), essa etapa era lenta, levava ao esgotamento do tempo limite de inicialização (timeout de 60s do Render), e causava erros frequentes como HTTP 502 Bad Gateway no deploy e HTTP 429 Too Many Requests do Yahoo Finance.

## Solução

Introduzir um método `async_fetch_with_retry` em `app/collectors/utils.py` com suporte ao interceptador do MT5 e ao limite de requisições por domínio. Refatorar o coletor `scanner_capitulacao.py` para usar chamadas HTTP assíncronas com o `httpx.AsyncClient` e usar `asyncio.Semaphore(2)` para limitar a concorrência a 2 e não disparar o rate limit do Yahoo Finance.

## Critérios de Aceite

1. O comportamento do painel do Scanner de Capitulação não muda na interface gráfica ou na saída da API `/api/snapshot`.
2. As requisições HTTP dentro do `scanner_capitulacao` são enviadas simultaneamente até o limite da concorrência (2).
3. O `async_fetch_with_retry` respeita o `MIN_DELAY` e recarrega os mesmos cabeçalhos que sua versão síncrona.
4. A inicialização da aplicação não atinge o timeout de deploy, eliminando ou minimizando drasticamente o HTTP 502 / HTTP 429 na inicialização do Render.
