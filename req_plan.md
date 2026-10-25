Execute the following plan:

1. Update `app/collectors/registro_fontes.py`:
   - Introduce `EndpointStat` dataclass: `ok: int = 0`, `falhas: int = 0`, `ultimo_status: int | None = None`.
   - Introduce `Falha` dataclass: `endpoint: str`, `simbolos: list[str]`, `status: int`, `corpo: str`.
   - Update `Fonte` dataclass to include:
     `endpoints: dict[str, EndpointStat] = field(default_factory=dict)`
     `falhas_recentes: list[Falha] = field(default_factory=list)` (keep last 10)
   - Update `sucesso` and `falha` to accept `endpoint` (str, default None), `simbolos` (list[str], default None), `status` (int, default None), `corpo` (str, default None).
   - In `sucesso`: update `endpoints[endpoint].ok` if `endpoint` provided. Maintain max 10 endpoints (e.g. by LRU or just limit insertion). Wait, the spec says "mantém, por fonte, um contador por endpoint ... com os 10 endpoints mais recentes". We'll use a standard dict and limit it to 10 by removing the oldest updated.
   - In `falha`: update `endpoints[endpoint].falhas` and `ultimo_status` if `endpoint` is provided. Append to `falhas_recentes` and keep last 10. `_SEGREDO.sub(r"\1***", corpo)[:200]`. Mask tokens in `corpo`.

2. Update `app/collectors/utils.py` inside `fetch_with_retry` and `async_fetch_with_retry`:
   - Extract `endpoint` and `simbolos` from the URL.
     - e.g., `/v8/finance/chart/{simbolo}`. We need a helper to normalize URLs.
     - For yfinance: `/v8/finance/chart/...`, `/v7/finance/spark?symbols=...`
   - Capture `response.text` safely to get the body for errors. (Max 200 chars, masked).
   - Call `registro_fontes.sucesso` with `endpoint`.
   - Call `registro_fontes.falha` with `endpoint`, `simbolos`, `status_code`, and `corpo`.

3. Update `app/services/sistema.py` to change how it determines the status of sources:
   - Adjust `_item_da_fonte` to check `falhas_recentes` or `endpoints` to determine level and detail.
   - If an endpoint has 3 consecutive 404s for different symbols and includes a known good symbol (we will hardcode or check if `^BVSP` is in the failed symbols), it's `PROBLEMA`.
   - Wait, "incluindo um símbolo que respondeu antes (`^BVSP`)" implies we should track which symbols are known good, or just check if `^BVSP` is one of them. The spec says `incluindo um símbolo que respondeu antes (^BVSP)`. So we'll check if `^BVSP` failed with 404 among the 3 consecutive fails.
   - If isolated 404s for specific symbols: `ATENCAO`.
   - Update the detail text: "os 3 endpoints com mais falhas, o status e o trecho do corpo".

4. Create `tests/test_aceite_090a.py` and implement acceptance criteria:
   - test: simulated 404 (respx) with known body gets recorded with endpoint, symbol, status and body snippet; token in body or URL masked.
   - test: 404 on whole endpoint (different symbols, including `^BVSP`) becomes `Problema` with endpoint text; isolated 404 becomes `Atenção`.
   - test: no secrets appear in `/sistema` or `/api/sistema`.

5. Run tests locally (`make verify` and `make smoke`).
6. Execute `make verify` and `make smoke` in the bash session to verify.
7. Complete pre commit steps to ensure proper testing, verification, review, and reflection are done.
