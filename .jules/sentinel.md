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
