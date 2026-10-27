"""As quatro raias de trabalho do agente e o que cada uma pode escrever (ADR 021).

Conflito só nasce onde duas sessões escrevem no mesmo lugar. Por isso o
trabalho é dividido pelo que cada raia escreve, e cada raia tem no máximo uma
sessão ativa e um PR aberto por vez:

    desenvolvimento  código, testes, documentação, o próprio núcleo; exclusiva
    especificacao    specs novas (Passo 7 e issues de feature), backlog, cadências
    revisao          a próxima spec da fila e a divisão de spec que falhou
    verificacao      achados sobre o que chegou à main, em arquivos próprios

O desenvolvimento não cria, não divide e não edita specs; só troca o
`status:` para `done` ao entregar (ADR 023).

As três raias auxiliares correm em paralelo com o desenvolvimento. A raia de
um PR sai do prefixo do título, e o título precisa bater com a persona da
sessão do Jules que abriu o PR (ADR 024): uma sessão do desenvolvedor não vira
raia de especificação só por intitular o PR `spec:`. O job `disciplina` do CI
(regra 8 do conferir_pr) reprova o PR que escreve fora da sua raia.

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
        ("docs/specs/", "docs/BACKLOG.md", "docs/runs/"),
    ),
    REVISAO: Raia(REVISAO, "revisao:", ("docs/specs/", "docs/runs/")),
    VERIFICACAO: Raia(VERIFICACAO, "verificacao:", (PASTA_VERIFICACAO,)),
    AUDITORIA: Raia(AUDITORIA, "auditoria:", ("docs/auditoria/", "auditoria/")),
}

# Autor dos PRs abertos pelo Jules. PR de outro autor (o dono do produto, outra
# ferramenta) não é do agente: o guardião não o cobra nem o fecha e ele não
# trava nenhuma raia (ADR 024).
AUTOR_DO_AGENTE = "google-labs-jules[bot]"


def do_agente(autor: str | None) -> bool:
    """Aceita o login da API REST (`google-labs-jules[bot]`) e o do gh
    (`app/google-labs-jules`)."""
    nome = (autor or "").removeprefix("app/").removesuffix("[bot]")
    return nome == AUTOR_DO_AGENTE.removesuffix("[bot]")


# Título da sessão do Jules (PERSONAS em adaptadores/jules.py) -> raia.
RAIA_DA_PERSONA = {
    "Desenvolvedor": DESENVOLVIMENTO,
    "Sentinel": DESENVOLVIMENTO,
    "Palette": DESENVOLVIMENTO,
    "Bolt": DESENVOLVIMENTO,
    "Especificador": ESPECIFICACAO,
    "Revisor": REVISAO,
    "Verificador": VERIFICACAO,
    "Auditor": AUDITORIA,
}

TAREFA_NO_CORPO = re.compile(r"jules\.google\.com/task/(\d+)")


def raia_da_sessao(titulo_sessao: str) -> str | None:
    """A raia de uma sessão pelo título dela; None se não é persona conhecida."""
    for persona, raia in RAIA_DA_PERSONA.items():
        if (titulo_sessao or "").startswith(persona):
            return raia
    return None


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


PASTA_SPECS = "docs/specs/"
_LINHA_STATUS = re.compile(r"^status:.*$", re.MULTILINE)


def edicao_de_spec_proibida(antes: str | None, depois: str | None) -> str:
    """Por que a raia de desenvolvimento não pode fazer esta mudança numa spec.

    O desenvolvimento não cria, não apaga e não reescreve specs: isso é das
    raias de especificação e de revisão (ADR 023). O único toque permitido é
    trocar a linha `status:` para `done` ao entregar a spec. Devolve o motivo,
    ou "" se a mudança é permitida.
    """
    if antes is None:
        return "spec nova"
    if depois is None:
        return "spec apagada"
    if _LINHA_STATUS.sub("", antes) != _LINHA_STATUS.sub("", depois):
        return "texto da spec alterado"
    m = re.search(r"^status:\s*([\w-]+)", depois, re.MULTILINE)
    if m and m.group(1) != "done" and depois != antes:
        return f"status mudado para `{m.group(1)}`"
    return ""


ID_DA_SPEC = re.compile(r"(?:^|/)(\d{3,4})([a-z]*)-[^/]*\.md$")


def spec_nova_fora_do_alvo(novas: list[str], alteradas: list[str]) -> list[str]:
    """Specs novas de um PR `revisão:` que não são partes de uma spec alterada.

    O Revisor só divide a spec que revisa, em `NNNa`, `NNNb`...; número novo é
    do Especificador, que o recebe reservado no prompt. O #548 dividiu a 093 em
    122 a 124 e podia colidir com a próxima spec do Especificador (ADR 024).
    """
    alvos = []
    for a in alteradas:
        m = ID_DA_SPEC.search(a)
        if m:
            alvos.append((int(m.group(1)), m.group(2)))
    fora = []
    for n in novas:
        m = ID_DA_SPEC.search(n)
        parte = m and any(
            int(m.group(1)) == num
            and m.group(2).startswith(letras)
            and len(m.group(2)) > len(letras)
            for num, letras in alvos
        )
        if not parte:
            fora.append(n)
    return sorted(fora)


REVISADA = re.compile(r"^revisada:\s*(\S.*?)\s*$", re.MULTILINE)


def revisada(texto: str) -> bool:
    """A spec tem o campo `revisada:` preenchido no cabeçalho."""
    return bool(REVISADA.search(texto or ""))
