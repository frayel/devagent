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

_SEGREDO = re.compile(
    r"([?&](?:token|key|apikey)=|\"(?:token|key|apikey)\"\s*:\s*\")[^&\"\s]+", re.I
)


@dataclass
class EndpointStat:
    ok: int = 0
    falhas: int = 0
    ultimo_status: int | None = None


@dataclass
class Falha:
    endpoint: str
    simbolos: list[str]
    status: int
    corpo: str


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
    endpoints: dict[str, EndpointStat] = field(default_factory=dict)
    falhas_recentes: list[Falha] = field(default_factory=list)


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


def sucesso(
    nome: str, quando: datetime | None = None, endpoint: str | None = None
) -> None:
    quando = quando or datetime.now(timezone.utc)
    with _trava:
        f = _fonte(nome)
        f.sucessos += 1
        f.ultimo_sucesso = quando
        _anotar(f, True)
        if endpoint:
            if endpoint not in f.endpoints:
                if len(f.endpoints) >= 10:
                    oldest = next(iter(f.endpoints))
                    del f.endpoints[oldest]
                f.endpoints[endpoint] = EndpointStat()
            f.endpoints[endpoint].ok += 1
            # Move para o fim para manter os 10 mais recentes acessados
            stat = f.endpoints.pop(endpoint)
            f.endpoints[endpoint] = stat


def falha(
    nome: str,
    motivo: str,
    quando: datetime | None = None,
    grave: bool = True,
    endpoint: str | None = None,
    simbolos: list[str] | None = None,
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

        if endpoint and status is not None:
            if endpoint not in f.endpoints:
                if len(f.endpoints) >= 10:
                    oldest = next(iter(f.endpoints))
                    del f.endpoints[oldest]
                f.endpoints[endpoint] = EndpointStat()
            stat = f.endpoints.pop(endpoint)
            stat.falhas += 1
            stat.ultimo_status = status
            f.endpoints[endpoint] = stat

            if corpo is not None:
                corpo = _SEGREDO.sub(r"\1***", corpo)[:200]
                # Regex adicional para 'Authorization'
                corpo = re.sub(
                    r'(?i)(Authorization\s*[:=]\s*)[^\s"\']+', r"\1***", corpo
                )[:200]
            else:
                corpo = ""

            f.falhas_recentes.append(
                Falha(
                    endpoint=endpoint,
                    simbolos=simbolos or [],
                    status=status,
                    corpo=corpo,
                )
            )
            del f.falhas_recentes[:-10]


def fontes() -> dict[str, Fonte]:
    """Cópia do registro, para quem só lê."""
    with _trava:
        return {
            nome: Fonte(
                nome=f.nome,
                sucessos=f.sucessos,
                falhas=f.falhas,
                ultimo_sucesso=f.ultimo_sucesso,
                ultima_falha=f.ultima_falha,
                ultimo_erro=f.ultimo_erro,
                recentes=list(f.recentes),
                graves=list(f.graves),
                endpoints={
                    k: EndpointStat(v.ok, v.falhas, v.ultimo_status)
                    for k, v in f.endpoints.items()
                },
                falhas_recentes=[
                    Falha(fa.endpoint, list(fa.simbolos), fa.status, fa.corpo)
                    for fa in f.falhas_recentes
                ],
            )
            for nome, f in _fontes.items()
        }


def limpar() -> None:
    with _trava:
        _fontes.clear()
