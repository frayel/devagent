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
