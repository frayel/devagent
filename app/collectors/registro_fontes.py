"""Saúde das fontes externas, vista pelas próprias chamadas dos coletores (spec 082).

Toda requisição que passa por `fetch_with_retry`, `async_fetch_with_retry` ou
pela mt5api deixa aqui o resultado final (depois dos retries). A página
`/sistema` lê este registro para dizer qual integração respondeu, qual falhou
e quando. Nada aqui faz requisição: é só memória do que já aconteceu.

O registro vive na memória do processo e recomeça quando o Render reinicia ou
acorda o serviço. A página diz isso ao lado dos números.
"""

from __future__ import annotations

import re
import threading
import urllib.parse
from dataclasses import dataclass, field
from datetime import datetime, timezone

# Domínio (ou trecho dele) → nome da integração exibido na página.
FONTES: tuple[tuple[str, str], ...] = (
    ("finance.yahoo.com", "Yahoo Finance"),
    ("brapi.dev", "brapi"),
    ("generativelanguage.googleapis.com", "Gemini"),
    ("moneytimes.com.br", "Money Times"),
    ("infomoney.com.br", "InfoMoney"),
)
MT5 = "MetaTrader 5"

_SEGREDO = re.compile(r"([?&](?:token|key|apikey)=)[^&\s]+", re.I)


@dataclass
class Fonte:
    nome: str
    sucessos: int = 0
    falhas: int = 0
    ultimo_sucesso: datetime | None = None
    ultima_falha: datetime | None = None
    ultimo_erro: str | None = None
    # Resultado das últimas chamadas, do mais antigo ao mais novo (True = ok).
    recentes: list[bool] = field(default_factory=list)
    # Alinhada com `recentes`: a falha indica a fonte fora do ar (rede, 5xx,
    # 429, chave recusada)? Um 404 é a fonte respondendo que o pedido não
    # existe: o defeito está em quem pediu, não na integração.
    graves: list[bool] = field(default_factory=list)
    endpoints: dict[str, dict] = field(default_factory=dict)


_fontes: dict[str, Fonte] = {}
_trava = threading.Lock()
MAX_RECENTES = 20


def nome_da_fonte(dominio: str) -> str:
    for trecho, nome in FONTES:
        if trecho in dominio:
            return nome
    return dominio


def _fonte(nome: str) -> Fonte:
    if nome not in _fontes:
        _fontes[nome] = Fonte(nome)
    return _fontes[nome]


def _anotar(fonte: Fonte, ok: bool, grave: bool = False) -> None:
    fonte.recentes.append(ok)
    fonte.graves.append(grave)
    del fonte.recentes[:-MAX_RECENTES]
    del fonte.graves[:-MAX_RECENTES]


def grave(status: int) -> bool:
    """Falha que indica a fonte indisponível, e não um pedido errado."""
    return status in (401, 403, 429) or status >= 500


_SEGREDO_CORPO = re.compile(
    r'("(?:token|key|apikey|authorization)"\s*:\s*)"[^"]+"', re.I
)
_SEGREDO_HEADER = re.compile(r"(authorization\s*:\s*(?:bearer\s+)?)[^\s\\]+", re.I)


def url_para_endpoint_e_simbolos(url: str) -> tuple[str, list[str]]:
    parsed = urllib.parse.urlparse(url)
    path = parsed.path
    query = urllib.parse.parse_qs(parsed.query)

    endpoint = path
    simbolos = []

    if "finance/chart/" in path:
        parts = path.split("finance/chart/")
        endpoint = parts[0] + "finance/chart/{simbolo}"
        if len(parts) > 1 and parts[1]:
            simbolos = [parts[1]]
    elif "finance/spark" in path:
        endpoint = path
        s = query.get("symbols", [""])[0] if "symbols" in query else ""
        if s:
            simbolos = s.split(",")
    elif "/api/quote/" in path:
        parts = path.split("/api/quote/")
        endpoint = parts[0] + "/api/quote/{simbolos}"
        if len(parts) > 1 and parts[1]:
            simbolos = parts[1].split(",")

    return endpoint, simbolos


def mascarar(texto: str) -> str:
    if not texto:
        return ""
    t = _SEGREDO.sub(r"\1***", texto)
    t = _SEGREDO_CORPO.sub(r'\1"***"', t)
    t = _SEGREDO_HEADER.sub(r"\1***", t)
    return t


def _anotar_endpoint(
    f: Fonte, url: str, status: int | None, corpo: str | None, ok: bool
):
    endpoint, simbolos = url_para_endpoint_e_simbolos(url)
    if endpoint not in f.endpoints:
        f.endpoints[endpoint] = {
            "ok": 0,
            "falhas": 0,
            "ultimo_status": None,
            "ultimo_corpo": None,
            "simbolos_ok": set(),
        }
    ep = f.endpoints[endpoint]

    if ok:
        ep["ok"] += 1
        for s in simbolos:
            ep["simbolos_ok"].add(s)
    else:
        ep["falhas"] += 1
        ep["ultimo_status"] = status
        ep["ultimo_corpo"] = mascarar(corpo)[:200] if corpo else None

        # Mantém apenas os 10 mais recentes
        if len(f.endpoints) > 10:
            mais_antigo = next(iter(f.endpoints))
            del f.endpoints[mais_antigo]

        # Reinsere para manter a ordem de inserção (LRU)
        e = f.endpoints.pop(endpoint)
        f.endpoints[endpoint] = e


def sucesso(nome: str, quando: datetime | None = None, url: str | None = None) -> None:
    quando = quando or datetime.now(timezone.utc)
    with _trava:
        f = _fonte(nome)
        f.sucessos += 1
        f.ultimo_sucesso = quando
        _anotar(f, True)
        if url:
            _anotar_endpoint(f, url, status=None, corpo=None, ok=True)


def falha(
    nome: str,
    motivo: str,
    quando: datetime | None = None,
    grave: bool = True,
    url: str | None = None,
    corpo: str | None = None,
    status: int | None = None,
) -> None:
    quando = quando or datetime.now(timezone.utc)
    with _trava:
        f = _fonte(nome)
        f.falhas += 1
        f.ultima_falha = quando
        f.ultimo_erro = mascarar(motivo)[:200]
        _anotar(f, False, grave)
        if url:
            _anotar_endpoint(f, url, status=status, corpo=corpo, ok=False)


def fontes() -> dict[str, Fonte]:
    """Cópia do registro, para quem só lê."""
    with _trava:
        return {
            nome: Fonte(
                f.nome,
                f.sucessos,
                f.falhas,
                f.ultimo_sucesso,
                f.ultima_falha,
                f.ultimo_erro,
                list(f.recentes),
                list(f.graves),
                {
                    k: {
                        "ok": v["ok"],
                        "falhas": v["falhas"],
                        "ultimo_status": v["ultimo_status"],
                        "ultimo_corpo": v["ultimo_corpo"],
                        "simbolos_ok": set(v["simbolos_ok"]),
                    }
                    for k, v in f.endpoints.items()
                },
            )
            for nome, f in _fontes.items()
        }


def limpar() -> None:
    with _trava:
        _fontes.clear()
