"""Escolha do modelo Gemini usado na extração de opiniões (ADR 006).

O Google aposenta modelos sem que o código fique sabendo: foi assim que a
extração parou com o `gemini-1.5-flash-8b`. Em vez de um nome fixo, o modelo
é descoberto pela própria API (`GET /v1beta/models`): o Flash-Lite estável de
versão mais alta que aceita `generateContent`. Preview, experimental e os
apelidos `-latest` ficam de fora, porque têm limites mais apertados na camada
gratuita e podem mudar de comportamento sem aviso.

Ordem de escolha:
1. `GEMINI_MODELO`, quando definida (escolha manual, nunca descartada);
2. o modelo descoberto, válido por 24 h;
3. se a listagem falhar, o último modelo que funcionou;
4. na falta dele, a lista de reserva abaixo.

Um 404 na geração descarta o modelo em uso e força nova descoberta.
"""

from __future__ import annotations

import logging
import os
import re
import threading
from datetime import datetime, timedelta, timezone

import httpx

from app.collectors import registro_fontes

logger = logging.getLogger(__name__)

LISTA_URL = "https://generativelanguage.googleapis.com/v1beta/models"
FONTE = "Gemini"
VALIDADE = timedelta(hours=24)
# Usada só quando a listagem falha e nenhum modelo funcionou ainda.
RESERVA = ("gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-2.5-flash-lite")

_ESTAVEL = re.compile(r"^gemini-(\d+(?:\.\d+)*)-flash-lite$")

_trava = threading.Lock()
_modelo: str | None = None
_origem: str | None = None  # "manual", "descoberto" ou "reserva"
_escolhido_em: datetime | None = None
_recusados: set[str] = set()


def _versao(nome: str) -> tuple[int, ...] | None:
    m = _ESTAVEL.match(nome)
    return tuple(int(p) for p in m.group(1).split(".")) if m else None


def escolher(modelos: list[dict], recusados: set[str] | None = None) -> str | None:
    """Flash-Lite estável mais novo da listagem da API, ou None."""
    recusados = recusados or set()
    candidatos = []
    for m in modelos:
        nome = str(m.get("name", "")).removeprefix("models/")
        if "generateContent" not in m.get("supportedGenerationMethods", []):
            continue
        versao = _versao(nome)
        if versao is None or nome in recusados:
            continue
        candidatos.append((versao, nome))
    return max(candidatos)[1] if candidatos else None


def _listar_modelos(api_key: str) -> list[dict]:
    modelos: list[dict] = []
    pagina: str | None = None
    try:
        while True:
            params: dict[str, str | int] = {"pageSize": 1000}
            if pagina:
                params["pageToken"] = pagina
            resp = httpx.get(
                LISTA_URL,
                headers={"x-goog-api-key": api_key},
                params=params,
                timeout=15.0,
            )
            if resp.status_code != 200:
                registro_fontes.falha(
                    FONTE,
                    f"HTTP {resp.status_code} ao listar modelos",
                    grave=registro_fontes.grave(resp.status_code),
                )
                resp.raise_for_status()
            dados = resp.json()
            modelos += dados.get("models", [])
            pagina = dados.get("nextPageToken")
            if not pagina:
                break
    except httpx.RequestError as e:
        registro_fontes.falha(FONTE, f"{type(e).__name__} ao listar modelos")
        raise
    registro_fontes.sucesso(
        FONTE,
        url="https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent",
    )
    return modelos


def modelo_atual(
    api_key: str, agora: datetime | None = None, forcar: bool = False
) -> str:
    """Nome do modelo a usar agora (sem o prefixo `models/`)."""
    global _modelo, _origem, _escolhido_em
    manual = os.environ.get("GEMINI_MODELO", "").strip()
    if manual:
        with _trava:
            _modelo, _origem = manual, "manual"
        return manual

    agora = agora or datetime.now(timezone.utc)
    with _trava:
        if (
            not forcar
            and _modelo
            and _origem == "descoberto"
            and _escolhido_em
            and agora - _escolhido_em < VALIDADE
        ):
            return _modelo
        recusados = set(_recusados)
        anterior = _modelo if _modelo not in recusados else None

    escolhido = None
    try:
        escolhido = escolher(_listar_modelos(api_key), recusados)
        if escolhido is None:
            logger.warning("Nenhum Flash-Lite estável na listagem de modelos do Gemini")
    except Exception as e:
        logger.warning(f"Falha ao listar modelos do Gemini: {type(e).__name__}")

    with _trava:
        if escolhido:
            _modelo, _origem, _escolhido_em = escolhido, "descoberto", agora
        elif anterior and _origem != "manual":
            # Mantém o que funcionava; tenta descobrir de novo na próxima rodada.
            _escolhido_em = None
        else:
            reserva = [r for r in RESERVA if r not in recusados] or list(RESERVA)
            _modelo, _origem, _escolhido_em = reserva[0], "reserva", None
        return _modelo or RESERVA[0]


def descartar(modelo: str) -> bool:
    """O modelo não existe mais (404). Devolve True se vale tentar outro."""
    global _escolhido_em
    if os.environ.get("GEMINI_MODELO", "").strip():
        return False
    with _trava:
        _recusados.add(modelo)
        _escolhido_em = None
    return True


def descricao() -> str | None:
    """Modelo em uso e como foi escolhido, para a página de sistema."""
    with _trava:
        if not _modelo:
            return None
        return f"{_modelo} ({_origem})"


def limpar() -> None:
    global _modelo, _origem, _escolhido_em
    with _trava:
        _modelo = _origem = _escolhido_em = None
        _recusados.clear()
