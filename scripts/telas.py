"""Capturas da interface para revisão visual (docs/DESIGN.md, seção 8).

Sobe a aplicação com um banco temporário preenchido com dados de DEMONSTRAÇÃO,
sem coleta automática, e salva duas capturas de página inteira:

    telas/desktop.png   1440 x 900
    telas/celular.png    390 x 844

Também confere se há rolagem horizontal em 390 px (sai com código 1 se houver).

Uso: make telas            (ou: python scripts/telas.py --saida telas)
     python scripts/telas.py --pagina docs/design/referencia.html   # só captura um HTML local

Os números da demonstração são inventados e vivem só no banco temporário:
nunca os copie para fixtures, testes ou produção.
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
TAMANHOS = {"desktop": (1440, 900), "celular": (390, 844)}


def _porta_livre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _semear(db_path: str) -> None:
    """Preenche o banco temporário com dados de demonstração."""
    os.environ["DATABASE_PATH"] = db_path
    sys.path.insert(0, str(RAIZ))
    import app.database as db

    db.DB_PATH = db_path
    db.init_db()
    agora = datetime.now(timezone.utc)

    datas, fechamentos, v = [], [], 96_000.0
    dia = datetime.now(timezone.utc).date() - timedelta(days=45)
    while len(datas) < 30:
        dia += timedelta(days=1)
        if dia.weekday() < 5:
            v *= 1 + (((len(datas) * 7919) % 23) - 10) / 1000
            datas.append(dia.isoformat())
            fechamentos.append(round(v, 2))

    db.save_ibovespa_data(
        db.IbovespaData(
            timestamp=agora,
            current_price=fechamentos[-1],
            previous_close=fechamentos[-2],
            history_json=json.dumps({"dates": datas, "closes": fechamentos}),
            fonte="demonstracao",
            mm21=sum(fechamentos[-21:]) / 21,
            mm200=fechamentos[0] * 0.97,
        )
    )

    def ativo(t: str, p: float, c: float) -> dict[str, object]:
        return {"ticker": t, "price": p, "change_percent": c}

    db.save_highlights_data(
        db.HighlightsData(
            timestamp=agora,
            highs_json=json.dumps(
                [
                    ativo("DEMO3", 21.4, 4.1),
                    ativo("TEST4", 9.8, 3.3),
                    ativo("FAKE3", 33.0, 2.2),
                    ativo("MOCK3", 12.5, 1.6),
                    ativo("SAMP11", 7.2, 0.9),
                ]
            ),
            lows_json=json.dumps(
                [
                    ativo("DUMY3", 5.1, -4.4),
                    ativo("FICT4", 18.3, -3.0),
                    ativo("XPTO3", 2.7, -2.1),
                    ativo("ZZZZ3", 44.0, -1.3),
                    ativo("ABCD3", 15.9, -0.7),
                ]
            ),
            fonte="demonstracao",
            up_count=18,
            down_count=12,
            total_count=30,
        )
    )
    db.save_volume_alerts_data(
        db.VolumeAlertsData(
            timestamp=agora,
            alerts_json=json.dumps(
                [
                    {"ticker": "DEMO3", "price": 21.4, "ratio": 3.1},
                    {"ticker": "FAKE3", "price": 33.0, "ratio": 2.2},
                    {"ticker": "MOCK3", "price": 12.5, "ratio": 1.7},
                ]
            ),
            fonte="demonstracao",
        )
    )
    db.save_atrasadas_rally_data(
        db.AtrasadasRallyData(
            timestamp=agora,
            rally_valido=True,
            top3_json=json.dumps(
                [
                    {"ticker": "VALE3", "retorno": -2.34},
                    {"ticker": "PETR4", "retorno": -1.50},
                    {"ticker": "ITUB4", "retorno": 0.80},
                ]
            ),
            fonte="demonstracao",
        )
    )
    db.save_dolar_correlation_data(
        db.DolarCorrelationData(
            timestamp=agora,
            positivas_json=json.dumps(
                [
                    {"ticker": "DEMO3", "correlation": 0.68},
                    {"ticker": "TEST4", "correlation": 0.52},
                    {"ticker": "FAKE3", "correlation": 0.41},
                ]
            ),
            negativas_json=json.dumps(
                [
                    {"ticker": "DUMY3", "correlation": -0.63},
                    {"ticker": "FICT4", "correlation": -0.55},
                    {"ticker": "XPTO3", "correlation": -0.37},
                ]
            ),
            fonte="demonstracao",
        )
    )
    # Painéis com gauge (spec 026): coesão, apetite a risco e rotação.
    db.save_coesao_data(
        db.CoesaoData(timestamp=agora, concordantes=7, total=10, fonte="demonstracao")
    )
    db.save_apetite_risco_data(
        db.ApetiteRiscoData(
            timestamp=agora, estado="Defensivo", diferenca=-0.8, fonte="demonstracao"
        )
    )
    db.save_rotacao_capital_data(
        db.RotacaoCapitalData(
            timestamp=agora,
            estado="Para Bancos",
            var_bancos=1.1,
            var_commodities=-0.4,
            fonte="demonstracao",
        )
    )


def _esperar(url: str, segundos: float = 30) -> None:
    fim = time.time() + segundos
    while time.time() < fim:
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                if r.status == 200:
                    return
        except OSError:
            time.sleep(0.3)
    raise SystemExit(f"A aplicação não respondeu em {url}")


def _capturar(url: str, saida: Path) -> int:
    from playwright.sync_api import sync_playwright

    saida.mkdir(parents=True, exist_ok=True)
    problemas = 0
    with sync_playwright() as pw:
        nav = pw.chromium.launch()
        for nome, (w, h) in TAMANHOS.items():
            pagina = nav.new_page(
                viewport={"width": w, "height": h}, color_scheme="dark"
            )
            pagina.goto(url, wait_until="networkidle")
            pagina.wait_for_timeout(800)  # gráficos terminam de desenhar
            arquivo = saida / f"{nome}.png"
            pagina.screenshot(path=str(arquivo), full_page=True)
            excesso = pagina.evaluate(
                "document.documentElement.scrollWidth - document.documentElement.clientWidth"
            )
            if excesso > 0:
                print(f"PROBLEMA: rolagem horizontal de {excesso}px em {nome} ({w}px)")
                problemas += 1
            print(f"captura: {arquivo}")
            pagina.close()
        nav.close()
    return 1 if problemas else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--saida", default="telas")
    ap.add_argument("--pagina", help="captura um HTML local em vez da aplicação")
    args = ap.parse_args()
    saida = RAIZ / args.saida

    if args.pagina:
        return _capturar((RAIZ / args.pagina).resolve().as_uri(), saida)

    with tempfile.TemporaryDirectory() as tmp:
        db_path = str(Path(tmp) / "demo.db")
        _semear(db_path)
        porta = _porta_livre()
        env = {**os.environ, "DATABASE_PATH": db_path, "COLETA_AUTOMATICA": "0"}
        proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(porta)],
            cwd=RAIZ,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            base = f"http://127.0.0.1:{porta}"
            _esperar(base + "/healthz")
            return _capturar(base + "/", saida)
        finally:
            proc.terminate()
            proc.wait(timeout=10)


if __name__ == "__main__":
    sys.exit(main())
