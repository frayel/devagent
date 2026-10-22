## 2026-09-26 - Add Security Headers
**Vulnerability:** Missing security headers (CSP, X-Frame-Options, etc.)
**Learning:** The application was missing basic security headers such as `X-Content-Type-Options`, `X-Frame-Options`, and `Strict-Transport-Security`, leaving it exposed to clickjacking and MIME-type sniffing attacks. Added a custom middleware to `FastAPI` app in `app/main.py` to enforce these headers on all responses.
**Prevention:** Always ensure security headers are configured using a middleware or similar mechanism for new APIs and web apps.

## 2026-09-29 - XSS vulnerability in template via `|safe`
**Vulnerability:** Cross-Site Scripting (XSS) due to raw JSON injection using `|safe`.
**Learning:** The application was injecting raw JSON into a script tag using Jinja's `|safe` filter (`{{ data.history_json | safe }}`). This allows an attacker who controls the JSON to break out of the string or object context and inject malicious scripts. Even though the current data source might be trusted, it's a bad practice. Replaced `|safe` with Jinja2's `|tojson` filter and exposed a dictionary instead of a JSON string. `tojson` correctly serializes the object to JSON while safely escaping HTML characters like `<` and `>`.
**Prevention:** Never use `|safe` with data that is ultimately derived from external sources or when serializing data for JavaScript blocks. Always use `|tojson` or equivalent safe serialization methods provided by the templating engine.

## 2026-09-27 - Content-Security-Policy and Pinned Dependencies
**Vulnerability:** Missing Content-Security-Policy header and unpinned dependencies in `requirements.txt`.
**Learning:** The previous security fix added some headers but missed Content-Security-Policy (CSP), which is important for mitigating XSS attacks. The application relies on external CDNs for scripts and styles (htmx, plotly). Added a CSP header to whitelist these sources. Additionally, dependencies in `requirements.txt` were unpinned, which could lead to supply chain attacks or accidental breakage from new vulnerable versions. Pinned versions.
**Prevention:** Always configure CSP with a strict whitelist of domains. Always pin dependencies in `requirements.txt` and check them with a tool like `pip-audit`.

## 2026-09-30 - Enforce Default HTTP Timeout in Collectors
**Vulnerability:** Missing default timeout on HTTP requests to external APIs (`httpx.get`).
**Learning:** `fetch_with_retry` lacked a strict default timeout. If not explicitly passed by the caller, `httpx.get` uses a default that may be too generous or could lead to the application hanging indefinitely (Resource Exhaustion / Denial of Service) if the remote service stops responding. Implemented a default 10.0-second timeout injected via `kwargs`.
**Prevention:** Always set explicit, reasonable timeouts for outbound network requests to avoid hanging threads and resource exhaustion.
## 2026-10-01 - Add Referrer-Policy and Permissions-Policy Headers
**Vulnerability:** Missing `Referrer-Policy` and `Permissions-Policy` headers.
**Learning:** The application lacked `Referrer-Policy` and `Permissions-Policy` headers. `Referrer-Policy` controls how much referrer information (sent with the Referer header) should be included with requests, protecting user privacy. `Permissions-Policy` allows site operators to disable access to browser features like the camera, microphone, and geolocation, reducing the attack surface. Added both to the global security middleware.
**Prevention:** Always include `Referrer-Policy` and `Permissions-Policy` headers in addition to other standard security headers to enhance user privacy and restrict unused browser capabilities.

## 2026-10-02 - Remove `| safe` from tables to prevent XSS
**Vulnerability:** Cross-Site Scripting (XSS) due to `| safe` in dynamic table cells.
**Learning:** The application was injecting formatted string combinations into table cells using Jinja's `| safe` filter in `app/templates/componentes.html`. Specifically, ticker symbols and formatted values were passed as raw strings and rendered using `{{ celula.conteudo | safe }}`. This could allow XSS if any displayed value contained malicious payloads (e.g. `ticker="<script>alert(1)</script>"`). To prevent this while still rendering safe HTML macros, I removed the `| safe` filter from `componentes.html` entirely and explicitly escaped and wrapped the dynamically formatted strings containing HTML (like `<span>`) in `| safe` before they were passed to the template inside `app/templates/index.html`.
**Prevention:** Never apply `| safe` globally to a variable that can contain arbitrary text. Instead, only apply `| safe` to specific sub-parts that construct static HTML elements after escaping the dynamic portions of the strings explicitly using Jinja's `| e` (escape) filter.

## 2026-10-03 - Remove `| safe` from kpi to prevent XSS
**Vulnerability:** Cross-Site Scripting (XSS) due to `| safe` in KPI variation string.
**Learning:** The application was using Jinja's `| safe` filter inside the `kpi` macro in `app/templates/componentes.html` to render the `variacao_str`. If any data within this string is attacker-controlled and unescaped, it can lead to XSS. I removed `| safe` from the macro and instead applied it explicitly in `app/templates/index.html` after passing the data. This follows the same pattern used previously to secure table components.
**Prevention:** Avoid applying `| safe` inside macros on variables that might contain dynamic unescaped text.

## 2026-10-04 - Remove `unsafe-eval` from Content-Security-Policy
**Vulnerability:** Cross-Site Scripting (XSS) potential due to `unsafe-eval` in CSP.
**Learning:** The Content-Security-Policy header in `app/main.py` included `'unsafe-eval'` in the `script-src` directive. This allows the execution of code injected into strings (e.g. via `eval()`, `setTimeout(string)`, etc). Since the application does not rely on `eval` in its JavaScript, removing it reduces the risk of XSS execution. Removed `'unsafe-eval'` from the middleware.
**Prevention:** Only include `'unsafe-eval'` in CSP if absolutely required by a trusted dependency and there's no alternative. By default, ensure it is absent to provide defense-in-depth against XSS.

## 2026-10-05 - Remove `unsafe-inline` from script-src in CSP
**Vulnerability:** Potential for Cross-Site Scripting (XSS) due to `'unsafe-inline'` in Content-Security-Policy (CSP) `script-src` directive.
**Learning:** The CSP configuration in `app/main.py` included `'unsafe-inline'` for `script-src` to allow inline scripts in `app/templates/base.html` (table bar formatting) and `app/templates/index.html` (filter buttons and plotly graph data generation). While convenient, this weakens XSS protections by permitting any injected script tags to execute. Extracted all inline scripts into a new external file `app/static/ui.js`. For the dynamic plotly graph, refactored it to read the `dates`, `closes`, and `is_positive` properties from `data-*` attributes populated securely via Jinja's `|tojson|e` filter.
**Prevention:** Avoid writing inline scripts `<script>...</script>`. Separate behavior (JavaScript) from markup (HTML/Jinja) by relying on external static files and passing dynamic data via `data-*` attributes. This enables a stricter CSP.

## 2026-10-06 - Remove `unsafe-inline` from style-src in CSP
**Vulnerability:** Potential for Cross-Site Scripting (XSS) due to `'unsafe-inline'` in Content-Security-Policy (CSP) `style-src` directive.
**Learning:** The CSP configuration in `app/main.py` included `'unsafe-inline'` for `style-src`. While it might be convenient for development, it allows inline styles, which can be leveraged for CSS injection attacks. I removed `'unsafe-inline'` from the `style-src` directive to strictly enforce that all styles are loaded from the allowed sources (in this case, 'self'). I also added `test_csp_no_unsafe_inline_style` in `tests/test_main.py` to assert its absence.
**Prevention:** Avoid using `'unsafe-inline'` in `style-src` as part of your CSP. Keep all styles in external CSS files.

## 2026-10-07 - Add request size limit middleware
**Vulnerability:** Missing request size limit on HTTP endpoints.
**Learning:** The FastAPI application lacked a mechanism to restrict the size of incoming HTTP request payloads. This exposes the server to Denial of Service (DoS) attacks where malicious actors could send excessively large payloads to consume memory and bandwidth. I added a custom middleware `limit_request_size` to `app/main.py` that intercepts all requests, checks the `Content-Length` header, and rejects payloads larger than 1MB with a `413 Payload Too Large` status code.
**Prevention:** Always implement size limits for incoming requests (e.g., via middleware or reverse proxy configuration) to mitigate resource exhaustion attacks.

## 2026-10-12 - Hide API Token from Collect Logs
**Vulnerability:** API Token leaked in error logs and diagnostics (Information Exposure).
**Learning:** Outbound HTTP requests to the `brapi` API contained a sensitive token in the query parameters (`?token=...`). When exceptions like `httpx.HTTPStatusError` or `httpx.RequestError` occurred, the unmasked URL was logged via the `logging` module and stored in the application state. This state was subsequently exposed via the unauthenticated diagnostic endpoint `/api/coleta`. I created a `_mask_secrets` utility in `app/agendador.py` that parses logs using a regular expression (`([?&]token=)[^&\s\\]+`) and replaces the token value with `***`. This sanitization was applied to both the general logger mechanism inside `_Memoria.emit` and the direct state update `estado["ultimo_erro"]`. I also updated `app/collectors/utils.py` to mask URLs before passing them to manual log warnings.
**Prevention:** Always mask, redact, or hash sensitive query parameters (e.g., `token`, `api_key`, `password`) and headers before logging URLs or exposing diagnostic state. Consider utilizing a structured logging framework with dedicated redaction filters.

## 2026-10-13 - Enhance API Token Masking in `app/agendador.py`
**Vulnerability:** Defense-in-depth for Information Exposure in diagnostics.
**Learning:** During the fix that masked API tokens from error logs via `_mask_secrets`, a few assignments in `app/agendador.py` such as `estado["detalhes"] = "\\n".join(memoria.linhas[-10:])` were not explicitly wrapped in `_mask_secrets` again at the point of serialization. While `memoria.linhas` already receives masked strings from `_Memoria.emit`, explicitly wrapping these variable assignments ensures that future refactors or direct appending to `memoria` won't leak tokens. Applied `_mask_secrets` directly to these lines.
**Prevention:** Always apply secret masking functions at the point of assignment to state variables to prevent accidental leaks through indirect paths.

## 2026-10-13 - Enforce Strict Content-Security-Policy (CSP) Directives
**Vulnerability:** Defense-in-depth for Cross-Site Scripting (XSS), Clickjacking, and malicious frame/base/object injection.
**Learning:** The existing Content-Security-Policy in `app/main.py` correctly locked down `script-src` and `style-src` but left out several directives that provide defense-in-depth against specific vector attacks. I added `object-src 'none'` to block Flash/applets, `base-uri 'self'` to prevent `<base>` tag injection from rewriting relative URLs, `form-action 'self'` to prevent form submissions to external malicious sites, and `frame-ancestors 'none'` to definitively block the site from being embedded in iframes (reinforcing X-Frame-Options). I updated the CSP headers in `add_security_headers` middleware and the corresponding tests in `tests/test_main.py`.
**Prevention:** Always configure comprehensive CSP policies by explicitly defining directives like `object-src`, `base-uri`, `form-action`, and `frame-ancestors` to restrict the browser capabilities and block multiple classes of injection.

## 2026-10-15 - Mask API Token in async_fetch_with_retry
**Vulnerability:** Defense-in-depth for Information Exposure in diagnostics.
**Learning:** The asynchronous request wrapper `async_fetch_with_retry` was logging unmasked URLs containing sensitive API tokens in query parameters when a request failed, exposing the token in diagnostic logs. I updated `app/collectors/utils.py` to mask the tokens using `re.sub` before the warning is logged, matching the logic in the synchronous equivalent.
**Prevention:** Always ensure both synchronous and asynchronous network request implementations consistently apply secret masking prior to logging.

## 2026-10-17 - Dependency audit check
**Vulnerability:** None found in project dependencies.
**Learning:** Ran `pip-audit -r requirements.txt`. No known vulnerabilities were found in the application's direct dependencies (`fastapi`, `uvicorn`, `jinja2`, `httpx`). The machine environment contained globally installed tools like `nltk` with known path traversal issues, but they are not part of the project. No actionable vulnerabilities were found in the codebase.
**Prevention:** Continue regular dependency audits with `pip-audit`.

## 2026-10-18 - Fix Database Connection Leaks
**Vulnerability:** Resource Exhaustion / Denial of Service (DoS) due to database connection leaks.
**Learning:** The methods `save_exaustao_queda_data`, `get_latest_exaustao_queda_data`, `save_mare_data`, `get_latest_mare_data`, `save_detector_acao_orfa_data` and `get_latest_detector_acao_orfa_data` in `app/database.py` were executing queries via `conn.execute()` without explicitly using a cursor or effectively managing the database resources, leading to potential connection leaks where `conn.close()` might not free all allocated resources properly. This can eventually lead to resource exhaustion and denial of service. I modified these functions to explicitly use `conn.cursor()` and execute the queries through the cursor.
**Prevention:** Always use `cursor = conn.cursor()` and execute queries via the cursor instead of directly on the connection object to ensure proper resource management and prevent connection leaks.

## 2026-10-19 - Nenhum risco imediato encontrado
**Vulnerability:** N/A.
**Learning:** Revisei logs e banco e dependências usando o pip-audit. Nenhum risco visível crítico e que possa ser mitigado em curto tempo foi encontrado.
**Prevention:** Executando repasse para o ciclo principal.

## 2026-10-20 - Nenhum risco imediato encontrado
**Vulnerability:** N/A.
**Learning:** Revisei logs, templates em busca de `| safe` inseguros e conexões do banco sem cursor para `execute`. Nenhum risco visível crítico e que possa ser mitigado em curto tempo foi encontrado.
**Prevention:** Executando repasse para o ciclo principal.

## 2026-10-21 - Nenhum risco imediato encontrado
**Vulnerability:** N/A.
**Learning:** Revisei dependências, templates em busca de `| safe` inseguros e configurações do Content-Security-Policy. Nenhum risco visível crítico e que possa ser mitigado em curto tempo foi encontrado.
**Prevention:** Executando repasse para o ciclo principal.

## 2026-10-22 - Nenhum risco imediato encontrado
**Vulnerability:** N/A.
**Learning:** Revisei dependências, templates em busca de `| safe` inseguros (são os mesmos verificados em outras iterações, que constroem a UI sem dados não confiáveis inseridos de forma direta) e queries de banco (todas as inserções usam placeholders). Testei a configuração de Content-Security-Policy e limites de request. Nenhum risco visível crítico e que possa ser mitigado em curto tempo foi encontrado.
**Prevention:** Executando repasse para o ciclo principal.
