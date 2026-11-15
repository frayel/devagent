"""Novidades do painel para o usuário (spec 156).

Lê `app/novidades.json`, escrito à mão no PR de cada mudança visível. O arquivo
é lido a cada chamada (poucas dezenas de linhas), sem cache: o teste troca o
caminho (`CAMINHO`) e o dia (`hoje`) por `monkeypatch`.

Arquivo ausente ou inválido não derruba página nenhuma: `carregar` devolve
`None`, o rodapé some, `/novidades` diz que estão indisponíveis e o snapshot
publica `novidades: []`. O erro vai para o log uma vez por processo.
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime
from itertools import groupby
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

CAMINHO = Path(__file__).resolve().parents[1] / "novidades.json"
FUSO = ZoneInfo("America/Sao_Paulo")
JANELA_DIAS = 60
TIPOS = {"novidade": "Novidade", "melhoria": "Melhoria", "correcao": "Correção"}

_erro_registrado = False


def hoje() -> date:
    """O dia de hoje no fuso do projeto (`[projeto].fuso` do devagent.toml)."""
    return datetime.now(FUSO).date()


def _registrar_erro(motivo: str) -> None:
    global _erro_registrado
    if not _erro_registrado:
        logger.error("Novidades indisponíveis: %s", motivo)
        _erro_registrado = True


def _valida(entrada: Any) -> bool:
    if not isinstance(entrada, dict):
        return False
    if entrada.get("tipo") not in TIPOS or not isinstance(entrada.get("texto"), str):
        return False
    try:
        date.fromisoformat(entrada["data"])
    except (KeyError, TypeError, ValueError):
        return False
    onde = entrada.get("onde")
    return onde is None or isinstance(onde, dict)


def carregar() -> list[dict[str, Any]] | None:
    """Todas as entradas do arquivo, ou `None` se ele está ausente ou inválido."""
    try:
        dados = json.loads(Path(CAMINHO).read_text(encoding="utf-8"))
    except (OSError, ValueError) as erro:
        _registrar_erro(f"{CAMINHO}: {erro}")
        return None
    if not isinstance(dados, list) or not all(_valida(e) for e in dados):
        _registrar_erro(f"{CAMINHO}: formato inválido")
        return None
    return dados


def _recentes(entradas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    dia = hoje()
    dentro = [
        e
        for e in entradas
        if 0 <= (dia - date.fromisoformat(e["data"])).days <= JANELA_DIAS
    ]
    return sorted(dentro, key=lambda e: e["data"], reverse=True)


def recentes() -> list[dict[str, Any]]:
    """Entradas dos últimos 60 dias, da mais nova para a mais antiga (snapshot)."""
    entradas = carregar()
    return _recentes(entradas) if entradas else []


def data_mais_recente() -> str | None:
    """`DD/MM/AAAA` da maior data do arquivo, mesmo fora da janela; `None` sem entradas."""
    entradas = carregar()
    if not entradas:
        return None
    maior = max(date.fromisoformat(e["data"]) for e in entradas)
    return maior.strftime("%d/%m/%Y")


def _onde_ver(onde: dict[str, Any] | None) -> dict[str, str] | None:
    if not onde:
        return None
    if onde.get("pagina"):
        rotulo = onde.get("pagina_nome") or onde["pagina"]
        if onde.get("painel"):
            rotulo = f"{rotulo} › {onde['painel']}"
        return {"href": onde["pagina"], "rotulo": rotulo}
    if onde.get("aba"):
        rotulo = onde.get("aba_nome") or onde["aba"]
        if onde.get("painel"):
            rotulo = f"{rotulo} › {onde['painel']}"
        return {"href": f"/?aba={onde['aba']}", "rotulo": rotulo}
    return None


def grupos() -> list[dict[str, Any]] | None:
    """Entradas da janela agrupadas por dia, para `/novidades`; `None` se indisponíveis."""
    entradas = carregar()
    if entradas is None:
        return None
    resultado = []
    for dia, itens in groupby(_recentes(entradas), key=lambda e: e["data"]):
        resultado.append(
            {
                "data": date.fromisoformat(dia).strftime("%d/%m/%Y"),
                "itens": [
                    {
                        "tipo": e["tipo"],
                        "selo": TIPOS[e["tipo"]],
                        "texto": e["texto"],
                        "onde": _onde_ver(e.get("onde")),
                    }
                    for e in itens
                ],
            }
        )
    return resultado
