"""As quatro raias de trabalho do agente e o que cada uma pode escrever (ADR 021).

Conflito só nasce onde duas sessões escrevem no mesmo lugar. Por isso o
trabalho é dividido pelo que cada raia escreve, e cada raia tem no máximo uma
sessão ativa e um PR aberto por vez:

    desenvolvimento  código, testes, documentação, o próprio núcleo; exclusiva
    especificacao    specs novas (Passo 7), o backlog de ideias e as cadências
    revisao          a próxima spec da fila, antes de ela ser implementada
    verificacao      achados sobre o que chegou à main, em arquivos próprios

As três raias auxiliares correm em paralelo com o desenvolvimento. A raia de
um PR sai do prefixo do título; o job `disciplina` do CI (regra 8 do
conferir_pr) reprova o PR que escreve fora da sua raia.

Só usa a biblioteca padrão.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

DESENVOLVIMENTO = "desenvolvimento"
ESPECIFICACAO = "especificacao"
REVISAO = "revisao"
VERIFICACAO = "verificacao"
AUDITORIA = "auditoria"

# Pasta dos achados do verificador; só a raia de verificação escreve nela.
PASTA_VERIFICACAO = "docs/verificacao/"


@dataclass(frozen=True)
class Raia:
    nome: str
    # Prefixo do título do PR, sem acento e em minúsculas.
    prefixo: str
    # Caminhos que a raia pode alterar; vazio = qualquer um, menos os reservados.
    permitidos: tuple[str, ...] = ()


RAIAS = {
    ESPECIFICACAO: Raia(
        ESPECIFICACAO,
        "spec:",
        ("docs/specs/", "docs/BACKLOG.md", "docs/STATE.md", "docs/runs/"),
    ),
    REVISAO: Raia(REVISAO, "revisao:", ("docs/specs/", "docs/runs/")),
    VERIFICACAO: Raia(VERIFICACAO, "verificacao:", (PASTA_VERIFICACAO,)),
    AUDITORIA: Raia(AUDITORIA, "auditoria:", ("docs/auditoria/", "auditoria/")),
}

# Caminhos que o desenvolvimento não escreve: pertencem a outra raia.
RESERVADOS_DO_DESENVOLVIMENTO = (PASTA_VERIFICACAO,)


def _sem_acento(texto: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", texto) if not unicodedata.combining(c)
    )


def raia_do_titulo(titulo: str) -> str:
    """A raia de um PR pelo prefixo do título; o resto é desenvolvimento.

    Aceita "revisão:" e "revisao:", "Spec:" e "spec:".
    """
    inicio = _sem_acento(titulo or "").strip().lower()
    for raia in RAIAS.values():
        if inicio.startswith(raia.prefixo):
            return raia.nome
    return DESENVOLVIMENTO


def do_desenvolvimento(titulo: str) -> bool:
    return raia_do_titulo(titulo) == DESENVOLVIMENTO


def fora_da_raia(raia: str, arquivos: list[str] | set[str]) -> list[str]:
    """Arquivos que a raia não pode alterar, em ordem.

    O auditor segue as regras da persona dele (devagent/agents/auditor.md) e
    não é conferido aqui.
    """
    if raia == AUDITORIA:
        return []
    if raia == DESENVOLVIMENTO:
        return sorted(
            a for a in arquivos if a.startswith(RESERVADOS_DO_DESENVOLVIMENTO)
        )
    permitidos = RAIAS[raia].permitidos
    return sorted(a for a in arquivos if not a.startswith(permitidos))


REVISADA = re.compile(r"^revisada:\s*(\S.*?)\s*$", re.MULTILINE)


def revisada(texto: str) -> bool:
    """A spec tem o campo `revisada:` preenchido no cabeçalho."""
    return bool(REVISADA.search(texto or ""))
