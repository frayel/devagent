"""Quem pode dar trabalho ao agente num repositório público.

O repositório é público e o ciclo é autônomo: o que o agente lê numa issue,
num comentário ou num PR vira tarefa, e o automerge leva a tarefa à produção.
Em 19/11 a revisão de segurança achou três caminhos para um estranho dirigir
o agente: a issue sem label virava `prioridade` em 24 h, o marcador de raia
no corpo de um PR o fazia passar por PR do agente, e o automerge mesclava PR
de fork com CI verde.

Daqui em diante só conta o que vem do dono, de membro ou colaborador do
repositório, ou de um GitHub App instalado nele (os bots do Actions e dos
agentes). O resto é dado, nunca ordem: fica de fora das filas.

Só usa a biblioteca padrão.
"""

from __future__ import annotations

from typing import Any

# `author_association` da API REST (ou `authorAssociation` do GraphQL/gh).
ASSOCIACOES_CONFIAVEIS = frozenset({"OWNER", "MEMBER", "COLLABORATOR"})


def autor_confiavel(item: dict[str, Any]) -> bool:
    """Issue, PR ou comentário escrito por quem pode mandar no repositório.

    Aceita o formato da API REST (`user`, `author_association`) e o do `gh`
    (`author`, `authorAssociation`, `is_bot`). Sem informação, não confia.
    """
    associacao = item.get("author_association") or item.get("authorAssociation")
    if str(associacao or "").upper() in ASSOCIACOES_CONFIAVEIS:
        return True
    autor = item.get("user") or item.get("author") or {}
    # Conta de GitHub App: só um App instalado neste repositório escreve nele.
    return autor.get("type") == "Bot" or autor.get("is_bot") is True


def so_confiaveis(itens: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [i for i in itens if autor_confiavel(i)]
