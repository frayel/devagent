"""Lê o devagent.toml do projeto.

O núcleo nunca escreve o nome do produto, a URL de produção ou o repositório
no código: tudo que muda de um projeto para outro vem deste arquivo.

Ordem de busca: variável DEVAGENT_CONFIG, depois devagent.toml no diretório
atual ou em algum diretório acima, depois ao lado da pasta devagent/.
Só usa a biblioteca padrão (tomllib, Python 3.11+).
"""

from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Any

NOME_ARQUIVO = "devagent.toml"

PADRAO: dict[str, Any] = {
    "projeto": {
        "nome": "este projeto",
        "repositorio": "",
        "producao_url": "",
        "fuso": "UTC",
        "termos_do_dominio": [],
    },
    "verificacao": {
        "verify": "make verify",
        "smoke": "make smoke",
        "audit": "make audit",
    },
    "deploy": {"adaptador": "render"},
}


def localizar(inicio: Path | None = None) -> Path | None:
    explicito = os.environ.get("DEVAGENT_CONFIG")
    if explicito:
        return Path(explicito)
    atual = (inicio or Path.cwd()).resolve()
    for pasta in (atual, *atual.parents):
        candidato = pasta / NOME_ARQUIVO
        if candidato.is_file():
            return candidato
    vizinho = Path(__file__).resolve().parent.parent / NOME_ARQUIVO
    return vizinho if vizinho.is_file() else None


def carregar(caminho: Path | None = None) -> dict[str, Any]:
    caminho = caminho or localizar()
    lido: dict[str, Any] = {}
    if caminho and caminho.is_file():
        with caminho.open("rb") as f:
            lido = tomllib.load(f)
    final: dict[str, Any] = {}
    for secao, valores in PADRAO.items():
        final[secao] = {**valores, **lido.get(secao, {})}
    for secao, valores in lido.items():
        final.setdefault(secao, valores)
    return final


CONFIG = carregar()
PROJETO: dict[str, Any] = CONFIG["projeto"]
VERIFICACAO: dict[str, Any] = CONFIG["verificacao"]
