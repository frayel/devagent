"""Auditor de produção do Painel B3.

Confere o que o site publicado mostra contra fontes independentes e contra
regras que qualquer dado verdadeiro obedece. Não lê o banco nem importa o
código da aplicação: olha para produção como um investidor olharia.

Uso:
    python -m auditoria.auditar                      # usa PRODUCTION_URL ou devagent.toml
    python -m auditoria.auditar --url https://...    # outra URL
    python -m auditoria.auditar --navegador          # também abre a página no Chromium
    python -m auditoria.auditar --saida relatorio/   # grava relatorio.json, .md e screenshot

Código de saída: 0 sem falhas · 1 alguma falha · 3 produção inacessível.
Avisos e checagens inconclusivas (por exemplo, fonte de referência fora do ar)
não reprovam, mas aparecem no relatório.

Só usa a biblioteca padrão. O modo --navegador precisa do Playwright.

O harness (resultado, relatório, checagens de aplicação e navegador) está no
núcleo, em devagent/auditoria/nucleo.py. Aqui ficam só as checagens deste produto.
"""

from __future__ import annotations

import json
import re
import sys
import urllib.request
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from auditoria import calendario
from devagent.auditoria import nucleo
from devagent.auditoria.nucleo import (
    AVISO,
    FALHA,
    INCONCLUSIVO,
    OK,
    Resultado,
    br,
    checar_navegador,
)

RAIZ = Path(__file__).resolve().parent.parent
FIXTURES = RAIZ / "tests" / "fixtures"
AVISO_LEGAL = "Não constitui recomendação de investimento"
USER_AGENT = "PainelB3-Auditor/1.0 (+https://github.com/frayel/devagent)"

# Limites. Mudar um destes números exige PR próprio com evidência (veja README).
TOLERANCIA_PRECO = 0.015  # 1,5% entre o valor exibido e a fonte independente
TOLERANCIA_FECHAMENTO = 0.005  # 0,5% nos fechamentos de pregões encerrados
IDADE_MAXIMA_NO_PREGAO = timedelta(minutes=45)
VARIACAO_DIARIA_MAXIMA = 12.0  # % (circuit breaker da B3 começa em 10%)
FAIXA_PLAUSIVEL = (40_000.0, 600_000.0)
HISTORICO_MINIMO = 15  # pregões no gráfico de 30 dias


def baixar(url: str, timeout: float = 30.0, tentativas: int = 1) -> tuple[int, str]:
    return nucleo.baixar(url, timeout, tentativas, user_agent=USER_AGENT)


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
    txt = (
        txt.strip()
        .replace("+", "")
        .replace("■", "")
        .replace("▼", "")
        .replace("▲", "")
        .strip()
    )
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
    m = re.search(r"([+\-■▼▲\s]*)([+\-]?[\d.,]+)\s*\(\s*([+\-]?[\d.,]+)\s*%\s*\)", html)
    if m:
        sinal = m.group(1) or ""
        val = m.group(2)
        if "-" in sinal and not val.startswith("-"):
            val = "-" + val
        elif "+" in sinal and not val.startswith("+"):
            val = "+" + val
        p.variacao = _numero_br(val)
        p.variacao_pct = _numero_br(m.group(3))
    m = re.search(
        r"(?:atualiza[çc][ãa]o:|·|&middot;)\s*(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}(?::\d{2})?)\s*(UTC|BRT)?",
        html,
        re.IGNORECASE,
    )
    if m:
        fmt = "%d/%m/%Y %H:%M:%S" if m.group(1).count(":") == 2 else "%d/%m/%Y %H:%M"
        tz = timezone.utc if (m.group(2) or "").upper() == "UTC" else calendario.BRT
        p.coletado_em = datetime.strptime(m.group(1), fmt).replace(tzinfo=tz)
    # Tenta extrair do atributo data-dates e data-closes (novo formato)
    m_dates = re.search(r"data-dates\s*=\s*'(\[.*?\])'", html)
    m_closes = re.search(r"data-closes\s*=\s*'(\[.*?\])'", html)
    if m_dates and m_closes:
        try:
            dates = json.loads(m_dates.group(1))
            closes = json.loads(m_closes.group(1))
            p.datas = [str(d)[:10] for d in dates]
            p.fechamentos = [float(c) for c in closes if c is not None]
        except (ValueError, TypeError):
            pass
    else:
        # Tenta o formato antigo
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
    return nucleo.numeros_dos_fixtures(pasta, 1_000, 10_000_000)


# --------------------------------------------------------------------------
# Checagens
# --------------------------------------------------------------------------


def checar_apetite_risco(snapshot: dict, pagina_html: str) -> None:
    """Valida invariantes do painel de Apetite a Risco."""
    painel = snapshot.get("paineis", {}).get("apetite_risco")
    assert painel, "Painel de Apetite a Risco não encontrado no snapshot"
    assert "estado" in painel, "Chave 'estado' faltando em apetite_risco no snapshot"
    assert "diferenca" in painel, (
        "Chave 'diferenca' faltando em apetite_risco no snapshot"
    )
    assert painel["estado"] in [
        "Tomando risco",
        "Defensivo",
        "Neutro",
        "indisponível",
    ], f"Estado '{painel['estado']}' inválido"


def checar_armadilha_abertura(snapshot: dict, pagina_html: str) -> None:
    """Valida invariantes do painel de Armadilha de Abertura."""
    painel = snapshot.get("paineis", {}).get("armadilha_abertura")
    assert painel is not None, (
        "Painel de Armadilha de Abertura não encontrado no snapshot"
    )
    if painel:
        if "alertas" in painel:
            assert isinstance(painel["alertas"], list), "'alertas' deve ser uma lista"


FAIXAS_MARE = ["Pânico", "Medo", "Neutro", "Confiança", "Otimismo extremo"]


def checar_volatilidade_silenciosa(snapshot: dict) -> list[Resultado]:
    """Valida invariantes do painel de Volatilidade Silenciosa (spec 028)."""
    painel = snapshot.get("paineis", {}).get("volatilidade_silenciosa")
    if painel is None:
        return [
            Resultado(
                "vol_sil.chave",
                FALHA,
                "Chave `volatilidade_silenciosa` ausente no /api/snapshot",
            )
        ]
    if not painel:
        return []

    alertas = painel.get("alertas", [])
    if not isinstance(alertas, list):
        return [Resultado("vol_sil.formato", FALHA, "'alertas' deve ser uma lista")]

    falhas = []
    for a in alertas:
        if abs(a.get("variacao", 100)) > 0.5:
            falhas.append(f"{a.get('ticker')}: variacao {a.get('variacao')} > 0.5%")

    if falhas:
        return [
            Resultado(
                "vol_sil.criterio",
                FALHA,
                "Ativos com variação fora do limite (<= 0.5%): " + ", ".join(falhas),
            )
        ]

    return [
        Resultado(
            "vol_sil.invariante", OK, "Volatilidade silenciosa respeita invariantes"
        )
    ]


def checar_mare(snapshot: dict) -> list[Resultado]:
    """Invariantes da Maré do mercado (spec 027), só com o que o snapshot publica."""
    m = snapshot.get("paineis", {}).get("mare")
    if m is None:
        return [Resultado("mare.chave", FALHA, "Chave `mare` ausente no /api/snapshot")]
    if not m:
        return [Resultado("mare.chave", AVISO, "Maré sem coleta válida ainda")]
    r: list[Resultado] = []
    valor = m.get("valor")
    comps = {k: v for k, v in (m.get("componentes") or {}).items() if v is not None}
    pesos = m.get("pesos") or {}
    numeros = [valor, *comps.values()]
    r.append(
        Resultado(
            "mare.escala",
            OK
            if all(isinstance(x, (int, float)) and 0 <= x <= 100 for x in numeros)
            else FALHA,
            "Maré e componentes entre 0 e 100",
            f"valor {valor}; componentes {comps}",
        )
    )
    if isinstance(valor, (int, float)) and 0 <= valor <= 100:
        esperada = FAIXAS_MARE[min(int(valor // 20), 4)]
        r.append(
            Resultado(
                "mare.faixa",
                OK if m.get("faixa") == esperada else FALHA,
                "Faixa coerente com o valor",
                f"valor {valor}: esperado {esperada}, publicado {m.get('faixa')}",
            )
        )
    r.append(
        Resultado(
            "mare.pesos",
            OK
            if abs(sum(pesos.values()) - 1) <= 0.001 and set(pesos) == set(comps)
            else FALHA,
            "Pesos dos componentes presentes somam 1",
            f"pesos {pesos}",
        )
    )
    if comps and set(pesos) == set(comps) and isinstance(valor, (int, float)):
        ponderada = sum(pesos[k] * comps[k] for k in comps)
        r.append(
            Resultado(
                "mare.media",
                OK if abs(ponderada - valor) <= 1 else FALHA,
                "Valor igual à média ponderada dos componentes (tolerância 1)",
                f"média {ponderada:.2f}; valor {valor}",
            )
        )
    historico = m.get("historico") or []
    coletado = str(m.get("coletado_em", ""))[:10]
    datas = [h.get("data", "") for h in historico]
    r.append(
        Resultado(
            "mare.historico",
            OK
            if len(historico) <= 21
            and datas == sorted(datas)
            and (not datas or datas[-1] <= coletado)
            else FALHA,
            "Histórico da Maré com até 21 pregões, em ordem, antes da coleta",
            f"{len(historico)} pontos; último {datas[-1] if datas else '-'}; coleta {coletado}",
        )
    )
    return r


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


# --------------------------------------------------------------------------
# Orquestração
# --------------------------------------------------------------------------


def checar_short_squeeze(snapshot: dict) -> Resultado | None:
    dados = snapshot.get("paineis", {}).get("short_squeeze")
    if dados is None:
        return Resultado(
            "short_squeeze.chave", AVISO, "Radar de short squeeze ausente no snapshot"
        )
    if dados and "alertas" not in dados:
        return Resultado("short_squeeze.chave", FALHA, "Chave 'alertas' ausente")
    return None


def checar_radar_inflexao(snapshot: dict) -> Resultado | None:
    dados = snapshot.get("paineis", {}).get("radar_inflexao")
    if dados is None:
        return Resultado("radar.chave", AVISO, "Radar de inflexão ausente no snapshot")
    if dados and "alertas" not in dados:
        return Resultado("radar.chave", FALHA, "Chave 'alertas' ausente")
    return None


def auditar(
    url: str,
    agora: datetime | None = None,
    navegador: bool = False,
    saida: Path | None = None,
    referencia: Callable[[str | None], tuple[Referencia | None, list[str]]] = (
        obter_referencia
    ),
    espera_coleta: float = 90.0,
) -> list[Resultado]:
    agora = agora or datetime.now(timezone.utc)
    url = url.rstrip("/")
    r: list[Resultado] = []

    # O Render hiberna e perde o disco; ao acordar, a app coleta em segundo
    # plano. checar_pagina espera essa primeira coleta antes de reprovar.
    r.append(nucleo.checar_saude(url))
    pagina, _, html = nucleo.checar_pagina(
        url,
        aviso_obrigatorio=AVISO_LEGAL,
        marcador_sem_dados="Dados não disponíveis",
        espera_sem_dados=espera_coleta,
    )
    r += pagina

    painel = extrair_do_html(html)
    s_status, s_corpo = baixar(f"{url}/api/snapshot", timeout=30)
    snap_dict = None
    if s_status == 200:
        try:
            snap_dict = json.loads(s_corpo)
            snap = extrair_do_snapshot(snap_dict)
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

        if isinstance(snap_dict, dict):
            r += checar_mare(snap_dict)
            r += checar_volatilidade_silenciosa(snap_dict)
            f_radar = checar_radar_inflexao(snap_dict)
            f_ss = checar_short_squeeze(snap_dict)
            if f_ss:
                r.append(f_ss)
            if f_radar:
                r.append(f_radar)
            try:
                checar_armadilha_abertura(snap_dict, html)
            except AssertionError as e:
                r.append(
                    Resultado(
                        "armadilha_abertura.invariante",
                        FALHA,
                        "Invariante de Armadilha de Abertura",
                        str(e),
                    )
                )
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


def main(argv: list[str] | None = None) -> int:
    return nucleo.executar(
        lambda url, agora, navegador, saida: auditar(url, agora, navegador, saida),
        __doc__.splitlines()[0],
        argv,
    )


if __name__ == "__main__":
    sys.exit(main())
