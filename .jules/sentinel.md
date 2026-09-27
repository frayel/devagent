## 2026-09-26 - Add Security Headers
**Vulnerability:** Missing security headers (CSP, X-Frame-Options, etc.)
**Learning:** The application was missing basic security headers such as `X-Content-Type-Options`, `X-Frame-Options`, and `Strict-Transport-Security`, leaving it exposed to clickjacking and MIME-type sniffing attacks. Added a custom middleware to `FastAPI` app in `app/main.py` to enforce these headers on all responses.
**Prevention:** Always ensure security headers are configured using a middleware or similar mechanism for new APIs and web apps.

## 2026-09-27 - Content-Security-Policy and Pinned Dependencies
**Vulnerability:** Missing Content-Security-Policy header and unpinned dependencies in `requirements.txt`.
**Learning:** The previous security fix added some headers but missed Content-Security-Policy (CSP), which is important for mitigating XSS attacks. The application relies on external CDNs for scripts and styles (htmx, plotly). Added a CSP header to whitelist these sources. Additionally, dependencies in `requirements.txt` were unpinned, which could lead to supply chain attacks or accidental breakage from new vulnerable versions. Pinned versions.
**Prevention:** Always configure CSP with a strict whitelist of domains. Always pin dependencies in `requirements.txt` and check them with a tool like `pip-audit`.