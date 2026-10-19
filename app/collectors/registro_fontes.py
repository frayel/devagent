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


def _anotar(fonte: Fonte, ok: bool) -> None:
    fonte.recentes.append(ok)
    del fonte.recentes[:-MAX_RECENTES]


def sucesso(nome: str, quando: datetime | None = None) -> None:
    quando = quando or datetime.now(timezone.utc)
    with _trava:
        f = _fonte(nome)
        f.sucessos += 1
        f.ultimo_sucesso = quando
        _anotar(f, True)


def falha(nome: str, motivo: str, quando: datetime | None = None) -> None:
    quando = quando or datetime.now(timezone.utc)
    with _trava:
        f = _fonte(nome)
        f.falhas += 1
        f.ultima_falha = quando
        f.ultimo_erro = _SEGREDO.sub(r"\1***", motivo)[:200]
        _anotar(f, False)


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
            )
            for nome, f in _fontes.items()
        }


def limpar() -> None:
    with _trava:
        _fontes.clear()
