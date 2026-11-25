"""Capturas da interface para revisão visual (docs/DESIGN.md, seção 8).

Sobe a aplicação com um banco temporário preenchido com dados de DEMONSTRAÇÃO,
sem coleta automática, e salva capturas de página inteira de cada página em
cada largura:

    telas/desktop.png e telas/celular.png              página inicial (1440 e 390 px)
    telas/<pagina>-<largura>.png                       as outras combinações

Em cada captura confere a regra de responsividade (PRODUTO.md, seção 6): a
página não rola para o lado, nenhum elemento sai da tela e nenhum texto vaza
da própria caixa. Tabela larga pode rolar dentro de um contêiner com
`overflow-x: auto`. Sai com código 1 se achar algum problema.

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
TAMANHOS = {
    "celular-pequeno": (360, 740),
    "celular": (390, 844),
    "tablet": (768, 1024),
    "desktop": (1440, 900),
}
# Páginas conferidas em cada largura (nome do arquivo, caminho).
PAGINAS = (("inicio", "/"), ("consultor", "/consultor"), ("sistema", "/sistema"))

# Elementos que saem da tela ou cujo texto vaza da caixa. Fica de fora o que
# está dentro de um contêiner que rola de propósito (overflow-x auto/scroll),
# dentro de <details> fechado ou dentro de SVG (gráficos desenham fora da
# caixa por natureza).
VAZAMENTOS_JS = r"""
() => {
  const vw = document.documentElement.clientWidth;
  const rola = (el) => /(auto|scroll)/.test(getComputedStyle(el).overflowX);
  const achados = [];
  for (const el of document.querySelectorAll('body *')) {
    if (el.closest('svg') || el.closest('details:not([open]) > :not(summary)')) continue;
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') continue;
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) continue;
    let anc = el.parentElement, protegido = false;
    while (anc) { if (rola(anc)) { protegido = true; break; } anc = anc.parentElement; }
    if (protegido) continue;
    const fora = r.right - vw > 1 || r.left < -1;
    const folha = el.children.length === 0 && (el.textContent || '').trim() !== '';
    const vaza = folha && !rola(el) && el.scrollWidth - el.clientWidth > 1;
    if (!fora && !vaza) continue;
    const nome = el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') +
      (typeof el.className === 'string' && el.className.trim()
        ? '.' + el.className.trim().split(/\s+/).join('.') : '');
    achados.push(`${nome} ${fora ? 'sai da tela' : 'texto vaza da caixa'} ` +
      `(direita ${Math.round(r.right)}px, tela ${vw}px): "${(el.textContent || '').trim().slice(0, 40)}"`);
  }
  return achados;
}
"""


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

    db.save_clima_global_data(
        db.ClimaGlobalData(
            timestamp=agora,
            sp500_pct=1.0,
            vix_pct=-3.0,
            status="Apetite a Risco",
            fonte="demonstracao",
        )
    )

    db.save_motores_indice_data(
        db.MotoresIndiceData(
            timestamp=agora,
            motores_json=json.dumps(
                [
                    {"nome": "Financeiro", "variacao": 1.83},
                    {"nome": "Commodities", "variacao": -0.45},
                    {"nome": "Doméstico", "variacao": 2.12},
                ]
            ),
            fonte="demonstracao",
        )
    )

    db.save_liquidez_abertura_data(
        db.LiquidezAberturaData(
            timestamp=agora,
            alertas_json=json.dumps(
                [
                    {"ticker": "VALE3", "ratio": 1.5, "var_pct": 2.5},
                    {"ticker": "PETR4", "ratio": 0.8, "var_pct": -1.2},
                ]
            ),
            fonte="yfinance (mock)",
        )
    )

    # O gráfico termina no pregão da coleta, como em produção: senão o
    # cabeçalho acusaria pregões mistos (spec 141).
    from app import calendario
    from app.services.carimbo import pregao_de

    dias = [pregao_de(agora)]
    while len(dias) < 30:
        dias.insert(0, calendario.pregao_anterior(dias[0]))
    datas, fechamentos, v = [], [], 96_000.0
    for dia in dias:
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

    # Pregões fechados no histórico, para o cabeçalho mostrar o seletor de
    # data como em produção (issue 885: no celular ele saía da tela).
    from app.banco import gravar_snapshot

    # O pregão de hoje fica com o snapshot ao vivo gravado acima.
    for i in range(len(dias) - 6, len(dias) - 1):
        gravar_snapshot(
            "ibovespa",
            dias[i],
            "final",
            "demonstracao",
            {
                "timestamp": agora.isoformat(),
                "current_price": fechamentos[i],
                "previous_close": fechamentos[i - 1],
                "history_json": json.dumps(
                    {"dates": datas[: i + 1], "closes": fechamentos[: i + 1]}
                ),
                "fonte": "demonstracao",
                "mm21": sum(fechamentos[i - 20 : i + 1]) / 21,
                "mm200": fechamentos[0] * 0.97,
            },
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
            media_simples_pct=0.45,
            media_simples_n=30,
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
    db.save_sensibilidade_juros_data(
        db.SensibilidadeJurosData(
            timestamp=agora,
            alertas_json=json.dumps(
                [
                    {"ticker": "LREN3", "correlation": -0.85},
                    {"ticker": "MGLU3", "correlation": -0.76},
                    {"ticker": "PETZ3", "correlation": -0.71},
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
    # Maré do mercado (spec 027), com 21 pregões de histórico.
    historico = []
    for i, v in enumerate(
        [
            31,
            35,
            42,
            40,
            47,
            52,
            49,
            55,
            58,
            54,
            51,
            54,
            57,
            60,
            63,
            59,
            62,
            65,
            61,
            64,
            66,
        ]
    ):
        dia = (agora - timedelta(days=(21 - i) * 7 // 5 + 1)).date().isoformat()
        historico.append({"data": dia, "valor": v})
    db.save_mare_data(
        db.MareData(
            timestamp=agora,
            valor=68,
            fluxo=74.0,
            calma=61.0,
            volume=67.0,
            # Heatmap da Maré: dez ativos, com pesos de 18% a 2%, para a
            # captura mostrar o treemap e o rótulo do menor tile.
            ativos_json=json.dumps(
                [
                    {"ticker": t, "variacao": v, "financeiro": p * 2e9, "peso": p}
                    for t, p, v in [
                        ("PETR4", 0.18, 1.0),
                        ("VALE3", 0.16, -0.6),
                        ("ITUB4", 0.14, 0.5),
                        ("BBAS3", 0.12, -1.8),
                        ("B3SA3", 0.10, 1.6),
                        ("WEGE3", 0.08, 3.1),
                        ("BPAC11", 0.08, -0.4),
                        ("SUZB3", 0.06, 0.0),
                        ("BBDC4", 0.05, 1.8),
                        ("PRIO3", 0.03, -4.2),
                    ]
                ]
            ),
            historico_json=json.dumps(historico),
            fonte="demonstracao",
        )
    )
    # Curva do dia da Maré (spec 175), para a captura mostrar o gráfico de
    # Marolas no dia BRT de hoje.
    from app.banco import gravar_snapshot
    from app.services.mare import hoje_brt

    gravar_snapshot(
        "mare_intradia",
        hoje_brt(),
        "ao_vivo",
        "demonstracao",
        {
            "data": hoje_brt().isoformat(),
            "pontos": [
                {"hora": f"{10 + i // 4:02d}:{(i % 4) * 15:02d}", "valor": v}
                for i, v in enumerate([58, 60, 57, 61, 63, 62, 64, 66, 65, 67, 68])
            ],
        },
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
    db.save_concentracao_setorial_data(
        db.ConcentracaoSetorialData(
            timestamp=agora,
            setor_destaque="Materiais Básicos",
            variacao_media=1.2,
            setor_lider_volume="Financeiro",
            volume_lider=1500000000.0,
            fonte="demonstracao",
        )
    )

    db.save_radar_short_squeeze_data(
        db.RadarShortSqueezeData(
            timestamp=agora, alertas_json="[]", fonte="demonstracao"
        )
    )

    db.save_assimetria_risco_retorno_data(
        db.AssimetriaRiscoRetornoData(
            timestamp=agora,
            alertas_json=json.dumps(
                [
                    {"ticker": "PETR4", "dist_min_pct": 1.2, "dist_max_pct": 15.4},
                    {"ticker": "VALE3", "dist_min_pct": 0.5, "dist_max_pct": 12.1},
                    {"ticker": "ITUB4", "dist_min_pct": 1.9, "dist_max_pct": 10.5},
                ]
            ),
            fonte="demonstracao",
        )
    )

    db.save_volatilidade_silenciosa_data(
        db.VolatilidadeSilenciosaData(
            timestamp=agora,
            alertas_json=json.dumps(
                [
                    {"ticker": "MOCK3", "amplitude": 5.4, "variacao": 0.2},
                    {"ticker": "FAKE4", "amplitude": 4.1, "variacao": -0.1},
                    {"ticker": "DEMO3", "amplitude": 3.8, "variacao": 0.4},
                ]
            ),
            fonte="demonstracao",
        )
    )

    db.save_fator_peso_pesado_data(
        db.FatorPesoPesadoData(
            timestamp=agora,
            proporcao=45.2,
            mercado_lateral=False,
            resumo_json=json.dumps([]),
            fonte="demonstracao",
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

    # Opiniões de demonstração para a lista Opiniões Recentes (spec 165): o
    # teste da issue 885 mede a página com a lista preenchida.
    from app.consultor.armazenamento import init_db as init_consultor
    from app.services.consultor_opinioes import save_opiniao

    init_consultor()
    # A lista só sai do ramo que tem a série do ^BVSP (sem ela o Consultor
    # devolve a página vazia); 30 pregões bastam, os ativos ficam sem sinal.
    from app.banco import gravar_serie

    gravar_serie(
        "^BVSP",
        [{"data": d, "close": c} for d, c in zip(datas, fechamentos)],
    )
    for guid, ticker, casa, rec, alvo, dias_atras in (
        ("demo-165-1", "PETR4", "Casa Demonstração A", "compra", 45.0, 1),
        ("demo-165-2", "PETR4", "Casa Demonstração B", "neutro", None, 2),
        ("demo-165-3", "PETR4", "Casa Demonstração A", "compra", None, 3),
        ("demo-165-4", "VALE3", "Casa Demonstração C", "venda", None, 2),
    ):
        save_opiniao(
            guid,
            ticker,
            casa,
            rec,
            alvo,
            f"Opinião de demonstração sobre {ticker}, com resumo longo o bastante para quebrar linha no celular.",
            "trecho de demonstração",
            (agora - timedelta(days=dias_atras)).isoformat(),
            f"https://exemplo.invalid/materia/{guid}",
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


def _vazamentos(pagina) -> list[str]:
    """Problemas de responsividade da página aberta (vazio = ok)."""
    problemas = []
    excesso = pagina.evaluate(
        "document.documentElement.scrollWidth - document.documentElement.clientWidth"
    )
    if excesso > 0:
        problemas.append(f"a página rola {excesso}px para o lado")
    # Só o mais externo de cada cadeia interessa: o filho de um elemento que
    # sai da tela também sai, e repetir não ajuda quem vai corrigir.
    vistos: list[str] = []
    for achado in pagina.evaluate(VAZAMENTOS_JS):
        if len(vistos) < 8:
            vistos.append(achado)
    return problemas + vistos


def _capturar(url: str, saida: Path, paginas=(("inicio", "/"),)) -> int:
    from playwright.sync_api import sync_playwright

    saida.mkdir(parents=True, exist_ok=True)
    problemas = 0
    with sync_playwright() as pw:
        nav = pw.chromium.launch(
            executable_path=os.environ.get("CHROMIUM_PATH") or None
        )
        for nome_pagina, caminho in paginas:
            for nome, (w, h) in TAMANHOS.items():
                pagina = nav.new_page(
                    viewport={"width": w, "height": h}, color_scheme="dark"
                )
                pagina.goto(
                    url.rstrip("/") + caminho if caminho != "/" else url,
                    wait_until="networkidle",
                )
                pagina.wait_for_timeout(800)  # gráficos terminam de desenhar
                prefixo = (
                    ""
                    if nome_pagina == "inicio" and nome in ("desktop", "celular")
                    else f"{nome_pagina}-"
                )
                arquivo = saida / f"{prefixo}{nome}.png"
                pagina.screenshot(path=str(arquivo), full_page=True)
                for p in _vazamentos(pagina):
                    print(f"PROBLEMA: {caminho} em {w}px: {p}")
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
            return _capturar(base + "/", saida, PAGINAS)
        finally:
            proc.terminate()
            proc.wait(timeout=10)


if __name__ == "__main__":
    sys.exit(main())
