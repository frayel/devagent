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