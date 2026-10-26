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
from urllib.parse import urlparse, parse_qs
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

_SEGREDO = re.compile(r"([?&]?(?:token|key|apikey|Authorization)[=\s]+)[^&\s]+", re.I)


def analisar_url(url: str) -> tuple[str, list[str]]:
    parsed = urlparse(url)
    parts = parsed.path.strip("/").split("/")
    symbols = []
    new_parts = []
    for p in parts:
        if not p:
            continue
        if (
            (p.isupper() and 2 <= len(p) <= 10)
            or p.endswith(".SA")
            or p.startswith("^")
        ):
            if p not in symbols:
                symbols.append(p)
            new_parts.append("{simbolo}")
        else:
            new_parts.append(p)
    endpoint = "/" + "/".join(new_parts)
    qs = parse_qs(parsed.query)
    for key in ["symbols", "symbol", "tickers", "ticker"]:
        if key in qs:
            for val in qs[key]:
                for s in val.split(","):
                    s = s.strip()
                    if s and s not in symbols:
                        symbols.append(s)
    return endpoint, symbols


@dataclass
class EndpointStats:
    ok: int = 0
    falhas: int = 0
    ultimo_status: int | str | None = None
    ultimo_corpo: str | None = None
    simbolos_ok: set[str] = field(default_factory=set)
    falhas_seguidas: list[tuple[list[str], int | str]] = field(default_factory=list)


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
    endpoints: dict[str, EndpointStats] = field(default_factory=dict)


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


def sucesso(nome: str, quando: datetime | None = None, url: str | None = None) -> None:
    quando = quando or datetime.now(timezone.utc)
    with _trava:
        f = _fonte(nome)
        f.sucessos += 1
        f.ultimo_sucesso = quando
        _anotar(f, True)
        if url:
            endpoint, simbolos = analisar_url(url)
            estat = f.endpoints.setdefault(endpoint, EndpointStats())
            estat.ok += 1
            estat.falhas_seguidas.clear()
            estat.simbolos_ok.update(simbolos)
            if len(f.endpoints) > 10:
                remover = sorted(
                    f.endpoints.items(), key=lambda x: x[1].ok + x[1].falhas
                )[0][0]
                del f.endpoints[remover]


def falha(
    nome: str,
    motivo: str,
    quando: datetime | None = None,
    grave: bool = True,
    url: str | None = None,
    status: int | None = None,
    corpo: str | None = None,
) -> None:
    quando = quando or datetime.now(timezone.utc)
    with _trava:
        f = _fonte(nome)
        f.falhas += 1
        f.ultima_falha = quando
        f.ultimo_erro = _SEGREDO.sub(r"\1***", motivo)[:200]
        _anotar(f, False, grave)
        if url:
            endpoint, simbolos = analisar_url(url)
            estat = f.endpoints.setdefault(endpoint, EndpointStats())
            estat.falhas += 1
            estat.ultimo_status = status
            corpo_limpo = _SEGREDO.sub(r"\1***", corpo)[:200] if corpo else None
            estat.ultimo_corpo = corpo_limpo
            estat.falhas_seguidas.append((simbolos, status or motivo))
            if len(f.endpoints) > 10:
                remover = sorted(
                    f.endpoints.items(), key=lambda x: x[1].ok + x[1].falhas
                )[0][0]
                del f.endpoints[remover]


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
                    k: EndpointStats(
                        v.ok,
                        v.falhas,
                        v.ultimo_status,
                        v.ultimo_corpo,
                        set(v.simbolos_ok),
                        list(v.falhas_seguidas),
                    )
                    for k, v in f.endpoints.items()
                },
            )
            for nome, f in _fontes.items()
        }


def limpar() -> None:
    with _trava:
        _fontes.clear()
