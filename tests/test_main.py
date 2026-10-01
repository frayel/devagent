from unittest import mock
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_healthz():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_xss_protection_in_history_json():
    with mock.patch("app.main.get_ibovespa_view_data") as mock_get_ibov:
        mock_get_ibov.return_value = {
            "current_price": "130.000",
            "variation": "+1.000",
            "variation_percent": "+0,78%",
            "is_positive": True,
            "is_negative": False,
            "time": "01/01/2026 12:00:00 UTC",
            "history_dict": {
                "dates": ["<script>alert(1)</script>"],
                "closes": [130000],
            },
            "fonte": "brapi",
            "mm21": None,
            "mm21_signal": None,
            "mm200": None,
            "mm200_signal": None,
        }

        with mock.patch("app.main.get_highlights_view_data") as mock_get_high:
            mock_get_high.return_value = None
            response = client.get("/")
            assert response.status_code == 200

            # Ensure the script tag is escaped by tojson
            assert "\\u003cscript\\u003ealert(1)\\u003c/script\\u003e" in response.text
            assert "<script>alert(1)</script>" not in response.text


def test_security_headers():
    response = client.get("/healthz")
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert (
        response.headers.get("Permissions-Policy")
        == "geolocation=(), microphone=(), camera=()"
    )
    assert (
        response.headers.get("Strict-Transport-Security")
        == "max-age=31536000; includeSubDomains"
    )
    csp = response.headers.get("Content-Security-Policy")
    assert csp is not None
    assert "default-src 'self'" in csp
    assert "https://unpkg.com" in csp
    assert "https://cdn.plot.ly" in csp
