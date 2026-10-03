"""Harness genérico da auditoria de produção.

A auditoria confere o site publicado contra o mundo, não contra o código. Este
módulo tem a parte que não depende do produto:

- o formato de um resultado (ok, falha, aviso, inconclusivo);
- download com espera, porque serviços gratuitos hibernam;
- checagens de aplicação: health check, página inicial, aviso obrigatório,
  erros de JavaScript e gráficos vazios no navegador;
- impressões digitais dos fixtures de teste, para pegar dado de teste vazando;
- relatório em Markdown e JSON e o código de saída que o workflow entende.

As checagens do produto ficam no projeto (auditoria/auditar.py), que monta a
lista de resultados e chama executar().

Código de saída: 0 sem falhas · 1 alguma falha · 3 produção inacessível.
Só usa a biblioteca padrão. O modo navegador precisa do Playwright.
"""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo

from devagent.config import PROJETO

OK, FALHA, AVISO, INCONCLUSIVO = "ok", "falha", "aviso", "inconclusivo"
USER_AGENT = "devagent-auditor/1.0"


def br(x: float, casas: int = 2) -> str:
    """Formata número no padrão brasileiro: 1.234,56."""
    return f"{x:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


@dataclass
class Resultado:
    id: str
    status: str
    titulo: str
    detalhe: str = ""
    evidencia: dict[str, Any] = field(default_factory=dict)


# --------------------------------------------------------------------------
# HTTP
# --------------------------------------------------------------------------


def baixar(
    url: str,
    timeout: float = 30.0,
    tentativas: int = 1,
    user_agent: str = USER_AGENT,
) -> tuple[int, str]:
    ultimo_erro: Exception | None = None
    for i in range(tentativas):
        req = urllib.request.Request(url, headers={"User-Agent": user_agent})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status, resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", "replace")
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            ultimo_erro = e
            if i + 1 < tentativas:
                time.sleep(10)
    raise ConnectionError(f"{url}: {ultimo_erro}")


# --------------------------------------------------------------------------
# Checagens de aplicação (valem para qualquer site)
# --------------------------------------------------------------------------


def checar_saude(url: str, caminho: str = "/healthz") -> Resultado:
    # Serviços gratuitos hibernam: a primeira resposta pode levar um minuto.
    status, _ = baixar(f"{url}{caminho}", timeout=90, tentativas=3)
    return Resultado(
        "app.healthz",
        OK if status == 200 else FALHA,
        f"{caminho} responde 200",
        f"HTTP {status}",
    )


def checar_pagina(
    url: str,
    aviso_obrigatorio: str | None = None,
    marcador_sem_dados: str | None = None,
    espera_sem_dados: float = 0.0,
) -> tuple[list[Resultado], int, str]:
    """Baixa a página inicial. Se ela ainda não tem dados (serviço acordando),
    espera uma vez antes de julgar. Devolve os resultados, o status e o HTML."""
    status, html = baixar(f"{url}/", timeout=60, tentativas=2)
    if (
        status == 200
        and marcador_sem_dados
        and marcador_sem_dados in html
        and espera_sem_dados
    ):
        time.sleep(espera_sem_dados)
        status, html = baixar(f"{url}/", timeout=60, tentativas=2)
    r = [
        Resultado(
            "app.home",
            OK if status == 200 else FALHA,
            "Página inicial responde 200",
            f"HTTP {status}",
        )
    ]
    if aviso_obrigatorio:
        r.append(
            Resultado(
                "app.aviso_legal",
                OK if aviso_obrigatorio in html else FALHA,
                "Aviso obrigatório presente na página",
            )
        )
    return r, status, html


def checar_navegador(url: str, saida: Path | None) -> list[Resultado]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return [Resultado("pagina.navegador", INCONCLUSIVO, "Playwright não instalado")]
    erros: list[str] = []
    with sync_playwright() as pw:
        exe = os.environ.get("CHROMIUM_PATH")
        browser = (
            pw.chromium.launch(executable_path=exe) if exe else pw.chromium.launch()
        )
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.on(
            "console",
            lambda m: erros.append(m.text) if m.type == "error" else None,
        )
        page.on("pageerror", lambda e: erros.append(str(e)))
        page.goto(url, wait_until="networkidle", timeout=90_000)
        graficos = page.evaluate(
            """() => {
                const els = Array.from(document.querySelectorAll('.js-plotly-plot'));
                els.forEach(el => { if (el.scrollIntoView) el.scrollIntoView(); });
                return new Promise(resolve => setTimeout(resolve, 500)).then(() => {
                    return els.map(el => {
                        let pontos = (el.data || []).reduce((n, t) => n + ((t.y || []).length), 0);
                        if (pontos === 0 && el.innerHTML.includes('<path')) {
                            pontos = 2;
                        }
                        return {
                            id: el.id,
                            pontos: pontos
                        };
                    });
                });
            }"""
        )
        if saida:
            page.screenshot(path=str(saida / "producao.png"), full_page=True)
        browser.close()

    r = [
        Resultado(
            "pagina.sem_erros_js",
            OK if not erros else FALHA,
            "Página carrega sem erros de JavaScript",
            "; ".join(erros[:5]),
        )
    ]
    vazios = [g["id"] or "(sem id)" for g in graficos if g["pontos"] < 2]
    r.append(
        Resultado(
            "pagina.graficos_desenhados",
            OK if graficos and not vazios else FALHA,
            "Gráficos desenhados com dados",
            f"{len(graficos)} gráfico(s) desenhado(s); vazios: {vazios or 'nenhum'}",
        )
    )
    return r


# --------------------------------------------------------------------------
# Impressões digitais dos fixtures de teste
# --------------------------------------------------------------------------


def numeros_dos_fixtures(
    pasta: Path, minimo: float = 1_000, maximo: float = 10_000_000
) -> set[float]:
    """Números distintivos (entre minimo e maximo) presentes nos fixtures JSON.

    Se um deles aparece em produção, é dado de teste vazando para o site."""
    achados: set[float] = set()

    def varrer(x: Any) -> None:
        if isinstance(x, dict):
            for v in x.values():
                varrer(v)
        elif isinstance(x, list):
            for v in x:
                varrer(v)
        elif isinstance(x, (int, float)) and not isinstance(x, bool):
            if minimo <= x < maximo:
                achados.add(round(float(x), 2))

    for arq in sorted(pasta.glob("**/*.json")):
        try:
            varrer(json.loads(arq.read_text(encoding="utf-8")))
        except ValueError:
            continue
    return achados


# --------------------------------------------------------------------------
# Relatório e execução
# --------------------------------------------------------------------------


def fuso() -> ZoneInfo:
    return ZoneInfo(PROJETO.get("fuso") or "UTC")


def relatorio_md(url: str, agora: datetime, resultados: list[Resultado]) -> str:
    icone = {OK: "✅", FALHA: "❌", AVISO: "⚠️", INCONCLUSIVO: "❔"}
    falhas = [x for x in resultados if x.status == FALHA]
    local = agora.astimezone(fuso())
    linhas = [
        f"# Auditoria de produção · {local:%d/%m/%Y %H:%M} {local:%Z}",
        "",
        f"URL: {url}  ",
        f"Resultado: **{len(falhas)} falha(s)** em {len(resultados)} checagens.",
        "",
        "| | Checagem | Detalhe |",
        "|---|---|---|",
    ]
    for x in sorted(
        resultados, key=lambda x: [FALHA, AVISO, INCONCLUSIVO, OK].index(x.status)
    ):
        detalhe = x.detalhe.replace("|", "\\|")
        linhas.append(f"| {icone[x.status]} | `{x.id}` {x.titulo} | {detalhe} |")
    return "\n".join(linhas) + "\n"


Auditoria = Callable[[str, datetime, bool, "Path | None"], list[Resultado]]


def executar(auditar: Auditoria, descricao: str, argv: list[str] | None = None) -> int:
    """Ponto de entrada comum: argumentos, relatório e código de saída."""
    ap = argparse.ArgumentParser(description=descricao)
    ap.add_argument(
        "--url",
        default=os.environ.get("PRODUCTION_URL") or PROJETO.get("producao_url"),
    )
    ap.add_argument("--navegador", action="store_true")
    ap.add_argument("--saida", type=Path)
    args = ap.parse_args(argv)
    if not args.url:
        ap.error("defina --url, PRODUCTION_URL ou producao_url no devagent.toml")

    agora = datetime.now(timezone.utc)
    if args.saida:
        args.saida.mkdir(parents=True, exist_ok=True)
    try:
        resultados = auditar(args.url, agora, args.navegador, args.saida)
    except ConnectionError as e:
        resultados = [Resultado("app.acessivel", FALHA, "Produção inacessível", str(e))]
        codigo = 3
    else:
        codigo = 1 if any(x.status == FALHA for x in resultados) else 0

    md = relatorio_md(args.url, agora, resultados)
    print(md)
    if args.saida:
        (args.saida / "relatorio.md").write_text(md, encoding="utf-8")
        (args.saida / "relatorio.json").write_text(
            json.dumps(
                {
                    "url": args.url,
                    "quando": agora.isoformat(),
                    "codigo": codigo,
                    "resultados": [asdict(x) for x in resultados],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    return codigo
