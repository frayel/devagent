"""Auditor de produção do Painel B3.

Confere o que o site publicado mostra contra fontes independentes e contra
regras que qualquer dado verdadeiro obedece. Não lê o banco nem importa o
código da aplicação: olha para produção como um investidor olharia.

Uso:
    python -m auditoria.auditar                      # usa PRODUCTION_URL
    python -m auditoria.auditar --url https://...    # outra URL
    python -m auditoria.auditar --navegador          # também abre a página no Chromium
    python -m auditoria.auditar --saida relatorio/   # grava relatorio.json, .md e screenshot

Código de saída: 0 sem falhas · 1 alguma falha · 3 produção inacessível.
Avisos e checagens inconclusivas (por exemplo, fonte de referência fora do ar)
não reprovam, mas aparecem no relatório.

Só usa a biblioteca padrão. O modo --navegador precisa do Playwright.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from auditoria import calendario

URL_PADRAO = "https://devagent-vb52.onrender.com"
RAIZ = Path(__file__).resolve().parent.parent
FIXTURES = RAIZ / "tests" / "fixtures"
AVISO_LEGAL = "Não constitui recomendação de investimento"
USER_AGENT = "PainelB3-Auditor/1.0 (+https://github.com/frayel/devagent)"

# Limites. Mudar qualquer um destes números exige revisão humana (veja README).
TOLERANCIA_PRECO = 0.015  # 1,5% entre o valor exibido e a fonte independente
TOLERANCIA_FECHAMENTO = 0.005  # 0,5% nos fechamentos de pregões encerrados
IDADE_MAXIMA_NO_PREGAO = timedelta(minutes=45)
VARIACAO_DIARIA_MAXIMA = 12.0  # % (circuit breaker da B3 começa em 10%)
FAIXA_PLAUSIVEL = (40_000.0, 600_000.0)
HISTORICO_MINIMO = 15  # pregões no gráfico de 30 dias


# --------------------------------------------------------------------------
# Resultado
# --------------------------------------------------------------------------

OK, FALHA, AVISO, INCONCLUSIVO = "ok", "falha", "aviso", "inconclusivo"


def br(x: float, casas: int = 2) -> str:
    """Formata número no padrão brasileiro: 183.476,86."""
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


def baixar(url: str, timeout: float = 30.0, tentativas: int = 1) -> tuple[int, str]:
    ultimo_erro: Exception | None = None
    for i in range(tentativas):
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
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
# O que produção mostra
# --------------------------------------------------------------------------


@dataclass
class Painel:
    """O painel do Ibovespa como o visitante vê."""

    origem: str  # "snapshot" ou "html"
    valor: float | None = None
    variacao: float | None = None
    variacao_pct: float | None = None
    fechamento_anterior: float | None = None
    coletado_em: datetime | None = None
    datas: list[str] = field(default_factory=list)
    fechamentos: list[float] = field(default_factory=list)
    fonte: str | None = None


def _numero_br(txt: str) -> float:
    """'130.000' -> 130000; '-1.234,5' -> -1234.5; '0.78' -> 0.78."""
    txt = txt.strip().replace("+", "")
    if "," in txt:
        return float(txt.replace(".", "").replace(",", "."))
    if re.fullmatch(r"-?\d{1,3}(\.\d{3})+", txt):
        return float(txt.replace(".", ""))
    return float(txt)


def extrair_do_html(html: str) -> Painel | None:
    if "Dados não disponíveis" in html:
        return None
    p = Painel(origem="html")
    m = re.search(r"([\d.,]+)\s*pontos", html)
    if m:
        p.valor = _numero_br(m.group(1))
    m = re.search(r"([+\-]?[\d.,]+)\s*\(\s*([+\-]?[\d.,]+)\s*%\s*\)", html)
    if m:
        p.variacao = _numero_br(m.group(1))
        p.variacao_pct = _numero_br(m.group(2))
    m = re.search(
        r"atualiza[çc][ãa]o:\s*(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}(?::\d{2})?)\s*(UTC|BRT)?",
        html,
        re.IGNORECASE,
    )
    if m:
        fmt = "%d/%m/%Y %H:%M:%S" if m.group(1).count(":") == 2 else "%d/%m/%Y %H:%M"
        tz = timezone.utc if (m.group(2) or "").upper() == "UTC" else calendario.BRT
        p.coletado_em = datetime.strptime(m.group(1), fmt).replace(tzinfo=tz)
    m = re.search(r"historyData\s*=\s*(\{.*?\})\s*;", html, re.DOTALL)
    if m:
        try:
            h = json.loads(m.group(1))
            p.datas = [str(d)[:10] for d in h.get("dates", [])]
            p.fechamentos = [float(c) for c in h.get("closes", []) if c is not None]
        except (ValueError, TypeError):
            pass
    if p.valor is not None and p.variacao is not None:
        p.fechamento_anterior = p.valor - p.variacao
    return p


def extrair_do_snapshot(dados: dict[str, Any]) -> Painel | None:
    ibov = (dados.get("paineis") or {}).get("ibovespa")
    if not ibov:
        return None
    hist = ibov.get("historico") or {}
    coletado = ibov.get("coletado_em")
    return Painel(
        origem="snapshot",
        valor=ibov.get("valor"),
        fechamento_anterior=ibov.get("fechamento_anterior"),
        variacao=(
            ibov["valor"] - ibov["fechamento_anterior"]
            if ibov.get("valor") is not None
            and ibov.get("fechamento_anterior") is not None
            else None
        ),
        variacao_pct=ibov.get("variacao_pct"),
        coletado_em=datetime.fromisoformat(coletado) if coletado else None,
        datas=[str(d)[:10] for d in hist.get("datas", [])],
        fechamentos=[float(c) for c in hist.get("fechamentos", [])],
        fonte=ibov.get("fonte"),
    )


# --------------------------------------------------------------------------
# Fontes independentes
# --------------------------------------------------------------------------


@dataclass
class Referencia:
    fonte: str
    valor: float | None
    fechamentos: dict[str, float]  # data ISO -> fechamento


def ref_yahoo() -> Referencia:
    url = "https://query2.finance.yahoo.com/v8/finance/chart/%5EBVSP?range=1mo&interval=1d"
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        d = json.load(resp)
    r = d["chart"]["result"][0]
    fech: dict[str, float] = {}
    for ts, c in zip(r["timestamp"], r["indicators"]["quote"][0]["close"]):
        if c is not None:
            dia = datetime.fromtimestamp(ts, tz=calendario.BRT).date().isoformat()
            fech[dia] = float(c)
    return Referencia(
        "Yahoo Finance (^BVSP)", r["meta"].get("regularMarketPrice"), fech
    )


def ref_stooq() -> Referencia:
    status, csv = baixar("https://stooq.com/q/d/l/?s=%5Ebvp&i=d", timeout=20)
    if status != 200 or not csv.startswith("Date"):
        raise ValueError(f"stooq respondeu {status}")
    fech: dict[str, float] = {}
    for linha in csv.strip().splitlines()[1:]:
        partes = linha.split(",")
        if len(partes) >= 5:
            fech[partes[0]] = float(partes[4])
    ultimo = fech[max(fech)] if fech else None
    return Referencia("Stooq (^BVP)", ultimo, dict(sorted(fech.items())[-40:]))


FONTES_REFERENCIA: list[Callable[[], Referencia]] = [ref_yahoo, ref_stooq]


def obter_referencia(evitar: str | None) -> tuple[Referencia | None, list[str]]:
    """Primeira fonte que responder, pulando a que produção declara usar."""
    erros: list[str] = []
    for f in FONTES_REFERENCIA:
        if evitar and evitar.lower() in f.__name__:
            continue
        try:
            return f(), erros
        except Exception as e:  # noqa: BLE001 - qualquer falha da fonte vale igual
            erros.append(f"{f.__name__}: {e}")
    return None, erros


# --------------------------------------------------------------------------
# Impressões digitais dos fixtures de teste
# --------------------------------------------------------------------------


def numeros_dos_fixtures(pasta: Path = FIXTURES) -> set[float]:
    """Números com cara de preço (>= 1000 e < 1e7) presentes nos fixtures."""
    achados: set[float] = set()

    def varrer(x: Any) -> None:
        if isinstance(x, dict):
            for v in x.values():
                varrer(v)
        elif isinstance(x, list):
            for v in x:
                varrer(v)
        elif isinstance(x, (int, float)) and not isinstance(x, bool):
            if 1_000 <= x < 10_000_000:
                achados.add(round(float(x), 2))

    for arq in sorted(pasta.glob("**/*.json")):
        try:
            varrer(json.loads(arq.read_text(encoding="utf-8")))
        except ValueError:
            continue
    return achados


# --------------------------------------------------------------------------
# Checagens
# --------------------------------------------------------------------------


def checar_coerencia(p: Painel) -> list[Resultado]:
    r: list[Resultado] = []
    if p.valor is None:
        return [
            Resultado("ibov.valor", FALHA, "Valor do Ibovespa não encontrado na página")
        ]

    lo, hi = FAIXA_PLAUSIVEL
    r.append(
        Resultado(
            "ibov.faixa",
            OK if lo <= p.valor <= hi else FALHA,
            "Valor dentro de uma faixa plausível",
            f"exibido {br(p.valor, 0)}; faixa aceita {br(lo, 0)} a {br(hi, 0)}",
        )
    )

    if p.variacao is not None and p.variacao_pct is not None and p.fechamento_anterior:
        esperado = p.variacao / p.fechamento_anterior * 100
        # A página arredonda pontos para inteiro; tolera o erro desse arredondamento.
        tol = 0.02 + 100 / p.fechamento_anterior
        r.append(
            Resultado(
                "ibov.variacao_coerente",
                OK if abs(esperado - p.variacao_pct) <= tol else FALHA,
                "Variação em % bate com a variação em pontos",
                f"exibido {p.variacao_pct:+.2f}%; calculado {esperado:+.2f}%",
            )
        )
        r.append(
            Resultado(
                "ibov.variacao_plausivel",
                OK if abs(p.variacao_pct) <= VARIACAO_DIARIA_MAXIMA else FALHA,
                "Variação diária plausível",
                f"{p.variacao_pct:+.2f}% (limite ±{VARIACAO_DIARIA_MAXIMA}%)",
            )
        )
    else:
        r.append(Resultado("ibov.variacao", FALHA, "Variação do dia não encontrada"))

    if not p.datas or len(p.datas) != len(p.fechamentos):
        r.append(
            Resultado(
                "ibov.historico",
                FALHA,
                "Histórico do gráfico ausente ou malformado",
                f"{len(p.datas)} datas, {len(p.fechamentos)} fechamentos",
            )
        )
        return r

    ordenado = all(a < b for a, b in zip(p.datas, p.datas[1:]))
    r.append(
        Resultado(
            "ibov.historico_ordem",
            OK if ordenado else FALHA,
            "Datas do histórico em ordem crescente e sem repetição",
        )
    )
    r.append(
        Resultado(
            "ibov.historico_tamanho",
            OK if len(p.datas) >= HISTORICO_MINIMO else FALHA,
            "Gráfico com pregões suficientes",
            f"{len(p.datas)} pregões (mínimo {HISTORICO_MINIMO})",
        )
    )
    salto = abs(p.fechamentos[-1] - p.valor) / p.valor * 100
    r.append(
        Resultado(
            "ibov.historico_vs_valor",
            OK if salto <= VARIACAO_DIARIA_MAXIMA else FALHA,
            "Último ponto do gráfico próximo do valor exibido",
            f"último fechamento {br(p.fechamentos[-1])}; valor {br(p.valor)}",
        )
    )
    return r


def checar_frescor(p: Painel, agora: datetime) -> list[Resultado]:
    r: list[Resultado] = []
    esperado = calendario.ultimo_pregao_iniciado(agora)
    tolerado = calendario.pregao_anterior(esperado)

    if p.datas:
        ultima = date.fromisoformat(p.datas[-1])
        r.append(
            Resultado(
                "ibov.historico_atual",
                OK if ultima >= tolerado else FALHA,
                "Gráfico chega até o pregão mais recente",
                f"última data {ultima.isoformat()}; pregão esperado {esperado.isoformat()}",
                {"ultima_data": ultima.isoformat(), "esperado": esperado.isoformat()},
            )
        )
        primeira = date.fromisoformat(p.datas[0])
        r.append(
            Resultado(
                "ibov.historico_janela",
                OK if (agora.date() - primeira).days <= 60 else FALHA,
                "Gráfico cobre só os últimos 30 pregões",
                f"primeira data {primeira.isoformat()}",
            )
        )

    if p.coletado_em is None:
        r.append(Resultado("ibov.coleta", FALHA, "Horário da coleta não exibido"))
        return r

    idade = agora - p.coletado_em
    if idade < timedelta(minutes=-5):
        r.append(
            Resultado(
                "ibov.coleta_futuro",
                FALHA,
                "Horário da coleta está no futuro",
                f"coleta {p.coletado_em.isoformat()}; agora {agora.isoformat()}",
            )
        )
    elif calendario.em_pregao(agora):
        r.append(
            Resultado(
                "ibov.coleta_recente",
                OK if idade <= IDADE_MAXIMA_NO_PREGAO else FALHA,
                "Coleta recente durante o pregão",
                f"coleta há {int(idade.total_seconds() // 60)} min "
                f"(limite {int(IDADE_MAXIMA_NO_PREGAO.total_seconds() // 60)} min)",
            )
        )
    else:
        dia_coleta = p.coletado_em.astimezone(calendario.BRT).date()
        r.append(
            Resultado(
                "ibov.coleta_do_ultimo_pregao",
                OK if dia_coleta >= esperado else FALHA,
                "Última coleta feita no pregão mais recente",
                f"coleta em {dia_coleta.isoformat()}; pregão esperado {esperado.isoformat()}",
            )
        )
    return r


def checar_fixtures(p: Painel, numeros: set[float]) -> list[Resultado]:
    if not numeros:
        return []
    suspeitos: list[str] = []
    if p.valor is not None and any(int(p.valor) == int(n) for n in numeros):
        suspeitos.append(f"valor {br(p.valor, 0)}")
    iguais = {round(c, 2) for c in p.fechamentos} & numeros
    if len(iguais) >= 2:
        suspeitos.append(f"fechamentos {sorted(iguais)}")
    return [
        Resultado(
            "ibov.sem_dado_de_teste",
            FALHA if suspeitos else OK,
            "Produção não exibe valores dos fixtures de teste",
            "; ".join(suspeitos) or "nenhum valor de tests/fixtures encontrado",
        )
    ]


def checar_referencia(
    p: Painel, ref: Referencia | None, erros: list[str], agora: datetime
) -> list[Resultado]:
    if ref is None:
        return [
            Resultado(
                "ibov.fonte_independente",
                INCONCLUSIVO,
                "Nenhuma fonte independente respondeu",
                "; ".join(erros),
            )
        ]
    r: list[Resultado] = []
    if p.valor is not None and ref.valor:
        dif = abs(p.valor - ref.valor) / ref.valor
        r.append(
            Resultado(
                "ibov.confere_com_fonte",
                OK if dif <= TOLERANCIA_PRECO else FALHA,
                f"Valor exibido confere com {ref.fonte}",
                f"exibido {br(p.valor)}; referência {br(ref.valor)}; "
                f"diferença {dif * 100:.2f}% (limite {TOLERANCIA_PRECO * 100:.1f}%)",
                {"exibido": p.valor, "referencia": ref.valor, "fonte": ref.fonte},
            )
        )
    hoje = agora.astimezone(calendario.BRT).date().isoformat()
    divergentes = []
    comparados = 0
    for d, c in zip(p.datas, p.fechamentos):
        if d == hoje or d not in ref.fechamentos:
            continue
        comparados += 1
        rc = ref.fechamentos[d]
        if abs(c - rc) / rc > TOLERANCIA_FECHAMENTO:
            divergentes.append(f"{d}: {br(c)} vs {br(rc)}")
    if comparados:
        r.append(
            Resultado(
                "ibov.historico_confere",
                OK if not divergentes else FALHA,
                f"Fechamentos do gráfico conferem com {ref.fonte}",
                f"{comparados} datas comparadas; divergentes: {divergentes[:5] or 'nenhuma'}",
            )
        )
    elif p.datas:
        r.append(
            Resultado(
                "ibov.historico_confere",
                FALHA,
                f"Nenhuma data do gráfico existe em {ref.fonte}",
                f"datas exibidas {p.datas[0]} a {p.datas[-1]}",
            )
        )
    return r


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
            """() => Array.from(document.querySelectorAll('.js-plotly-plot')).map(el => ({
                id: el.id,
                pontos: (el.data || []).reduce((n, t) => n + ((t.y || []).length), 0)
            }))"""
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
# Orquestração
# --------------------------------------------------------------------------


def auditar(
    url: str,
    agora: datetime | None = None,
    navegador: bool = False,
    saida: Path | None = None,
    referencia: Callable[[str | None], tuple[Referencia | None, list[str]]] = (
        obter_referencia
    ),
) -> list[Resultado]:
    agora = agora or datetime.now(timezone.utc)
    url = url.rstrip("/")
    r: list[Resultado] = []

    # O plano gratuito do Render hiberna: a primeira resposta pode levar um minuto.
    status, _ = baixar(f"{url}/healthz", timeout=90, tentativas=3)
    r.append(
        Resultado(
            "app.healthz",
            OK if status == 200 else FALHA,
            "/healthz responde 200",
            f"HTTP {status}",
        )
    )

    status, html = baixar(f"{url}/", timeout=60, tentativas=2)
    r.append(
        Resultado(
            "app.home",
            OK if status == 200 else FALHA,
            "Página inicial responde 200",
            f"HTTP {status}",
        )
    )
    r.append(
        Resultado(
            "app.aviso_legal",
            OK if AVISO_LEGAL in html else FALHA,
            "Aviso legal presente na página",
        )
    )

    painel = extrair_do_html(html)
    s_status, s_corpo = baixar(f"{url}/api/snapshot", timeout=30)
    if s_status == 200:
        try:
            snap = extrair_do_snapshot(json.loads(s_corpo))
        except (ValueError, KeyError, TypeError) as e:
            snap = None
            r.append(
                Resultado(
                    "app.snapshot", FALHA, "/api/snapshot fora do contrato", str(e)
                )
            )
        if snap and painel and painel.valor is not None and snap.valor is not None:
            r.append(
                Resultado(
                    "app.snapshot_igual_tela",
                    OK if int(snap.valor) == int(painel.valor) else FALHA,
                    "/api/snapshot mostra o mesmo valor que a página",
                    f"snapshot {br(snap.valor)}; página {br(painel.valor, 0)}",
                )
            )
        painel = snap or painel
    else:
        r.append(
            Resultado(
                "app.snapshot",
                AVISO,
                "/api/snapshot ainda não existe; auditoria feita pelo HTML",
                "Veja o contrato em auditoria/README.md",
            )
        )

    if painel is None:
        r.append(
            Resultado("ibov.painel", FALHA, "Painel do Ibovespa sem dados em produção")
        )
    else:
        r += checar_coerencia(painel)
        r += checar_frescor(painel, agora)
        r += checar_fixtures(painel, numeros_dos_fixtures())
        ref, erros = referencia(painel.fonte)
        r += checar_referencia(painel, ref, erros, agora)

    if navegador:
        r += checar_navegador(url + "/", saida)
    return r


def relatorio_md(url: str, agora: datetime, resultados: list[Resultado]) -> str:
    icone = {OK: "✅", FALHA: "❌", AVISO: "⚠️", INCONCLUSIVO: "❔"}
    falhas = [x for x in resultados if x.status == FALHA]
    linhas = [
        f"# Auditoria de produção · {agora.astimezone(calendario.BRT):%d/%m/%Y %H:%M} BRT",
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


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--url", default=os.environ.get("PRODUCTION_URL") or URL_PADRAO)
    ap.add_argument("--navegador", action="store_true")
    ap.add_argument("--saida", type=Path)
    args = ap.parse_args(argv)

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


if __name__ == "__main__":
    sys.exit(main())
