from playwright.sync_api import sync_playwright
import time
import subprocess
import os
import httpx


def test_csp_issue_no_errors():
    """
    Testes de regressão para a issue 625 onde os inline-styles quebravam o Content-Security-Policy
    e as exibições no heatmap.
    """
    # Start the server
    env = os.environ.copy()
    env["CONSULTOR_SENHA"] = ""
    env["DATABASE_PATH"] = "test.db"
    env["COLETA_AUTOMATICA"] = "0"

    server_process = subprocess.Popen(
        ["uvicorn", "app.main:app", "--port", "8005"],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        # Wait for server to start
        for _ in range(10):
            try:
                if httpx.get("http://127.0.0.1:8005/healthz").status_code == 200:
                    break
                time.sleep(1)
            except httpx.RequestError:
                time.sleep(1)

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()

            errors = []
            page.on("pageerror", lambda err: errors.append(err.message))
            page.on(
                "console",
                lambda msg: errors.append(msg.text) if msg.type == "error" else None,
            )

            response = page.goto("http://127.0.0.1:8005")
            assert response.status == 200, "A página inicial deve retornar 200 OK"

            time.sleep(1)

            csp_errors = [e for e in errors if "Content Security Policy" in e]
            assert not csp_errors, f"CSP errors found: {csp_errors}"
    finally:
        server_process.terminate()
        server_process.wait()
