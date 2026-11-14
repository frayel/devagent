"""Qual papel esta sessão assume e qual é o alvo concreto dela (ADR 033).

Uma raia que para trava as outras: sem o Revisor, nenhuma spec chega ao
desenvolvimento; sem o Especificador, a fila seca. Enquanto havia um
orquestrador externo, era ele quem abria a sessão de cada raia com o alvo no
prompt. Quando ele saiu e ninguém ficou no lugar, a fila inteira esperou a
revisão e o desenvolvimento passou dez rodadas seguidas melhorando a si mesmo.

Aqui a decisão volta para o código, sem depender de quem agenda as sessões:

    python -m devagent.papel               # o papel desta sessão
    python -m devagent.papel revisor       # o alvo de uma persona nomeada
    python -m devagent.papel especificador
    python -m devagent.papel verificador

Sem argumento, a sessão é do desenvolvedor, salvo quando ele não tem trabalho
de produto e outra raia está parada: aí a sessão assume essa raia por inteiro
(a persona de `devagent/agents/raias.md`, não o ciclo). O `estado_github`
imprime a mesma decisão no primeiro comando.

As funções de decisão são puras; só o `main` consulta o GitHub e o git.
Só usa a biblioteca padrão.
"""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from devagent.fila_specs import (
    fila_da_revisao,
    fila_do_desenvolvimento,
    issue_prioritaria,
    producao_pendente,
    proximo_numero,
    spec_para_dividir,
    specs_prontas,
    tentativas_da_spec,
)
from devagent.raias import (
    DESENVOLVIMENTO,
    ESPECIFICACAO,
    PASTA_VERIFICACAO,
    REVISAO,
    VERIFICACAO,
    raia_do_titulo,
)

DESENVOLVEDOR = "desenvolvedor"
REVISOR = "revisor"
ESPECIFICADOR = "especificador"
VERIFICADOR = "verificador"

RAIA_DA_PERSONA = {
    REVISOR: REVISAO,
    ESPECIFICADOR: ESPECIFICACAO,
    VERIFICADOR: VERIFICACAO,
}
NOME = {
    DESENVOLVEDOR: "desenvolvedor",
    REVISOR: "Revisor",
    ESPECIFICADOR: "Especificador",
    VERIFICADOR: "Verificador",
}

# Com a fila de specs ready neste tamanho ou menor, o Especificador prepara a
# próxima (ADR 029).
FILA_PARA_ESPECIFICAR = 2
# Entregas seguidas da raia de desenvolvimento sem nenhuma spec, com spec ready
# na fila, a partir das quais a fila é tratada como travada.
LIMITE_SEM_SPEC = 4
# Sem relatório anterior (ou com um antigo), o Verificador olha só este período.
JANELA_DA_VERIFICACAO = timedelta(hours=24)

ENTREGA_DE_SPEC = re.compile(r"^(feat|refactor)\b", re.IGNORECASE)
RELATORIO = re.compile(r"(\d{4})-(\d{2})-(\d{2})-(\d{2})(\d{2})\.md$")


@dataclass(frozen=True)
class Papel:
    persona: str
    # Por que a sessão é desta persona.
    motivo: str
    # O trabalho concreto; vazio quando a persona não tem o que fazer.
    alvo: str = ""

    def frase(self) -> str:
        """O que o `estado_github` imprime no primeiro comando."""
        if self.persona == DESENVOLVEDOR:
            return " ".join(t for t in (self.motivo, self.alvo) if t)
        return (
            f"Esta sessão atua como {NOME[self.persona]}, não como desenvolvedor: "
            f"{self.motivo} Siga `devagent/agents/raias.md` e ignore o ciclo de "
            f"decisão. {self.alvo}"
        )


def _relativo(caminho: Path, raiz: Path | None = None) -> str:
    try:
        return caminho.relative_to(raiz or Path.cwd()).as_posix()
    except ValueError:
        return caminho.as_posix()


def pr_travado(raia: str, prs: list[dict[str, Any]]) -> dict[str, Any] | None:
    """O PR aberto da raia, se o CI falhou ou há conflito: ninguém mais o salva."""
    for p in prs:
        if p.get("raia") != raia:
            continue
        if str(p.get("ci", "")).startswith("falhou") or p.get("merge") == "dirty":
            return p
    return None


def _com_pr(raia: str, prs: list[dict[str, Any]]) -> bool:
    return any(p.get("raia") == raia for p in prs)


def _destravar(p: dict[str, Any]) -> str:
    return (
        f"O PR #{p['numero']} desta raia está parado (CI: {p.get('ci')}, merge: "
        f"{p.get('merge')}). A tarefa da sessão é destravá-lo na branch dele "
        f"(`{p.get('branch')}`), pela skill `devagent/skills/destravar-pr.md`. "
        "Não abra PR novo."
    )


def trabalho_do_desenvolvimento(
    prontas: list[Path],
    issues: list[dict[str, Any]],
    prs: list[dict[str, Any]],
    producao_quebrada: bool = False,
) -> str:
    """Por que a sessão é do desenvolvedor; vazio se ele não tem trabalho de produto.

    Passos 5 e 6 não contam: eles existem para a volta em que o resto está em
    dia, não para ocupar a sessão enquanto outra raia segura a fila.
    """
    if any(p.get("do_agente") for p in prs):
        return "Existe PR aberto da raia de desenvolvimento."
    if producao_quebrada or producao_pendente(issues):
        return "A produção acusa problema."
    if issue_prioritaria(issues):
        return "Existe issue `prioridade` aberta."
    fila = fila_do_desenvolvimento(prontas)
    if fila and not tentativas_da_spec(fila[0], issues):
        return "Há spec revisada na fila."
    return ""


def alvo_do_revisor(
    prontas: list[Path],
    issues: list[dict[str, Any]],
    prs: list[dict[str, Any]],
    raiz: Path | None = None,
) -> str:
    travado = pr_travado(REVISAO, prs)
    if travado:
        return _destravar(travado)
    if _com_pr(REVISAO, prs):
        return ""
    dividir = spec_para_dividir(prontas, issues)
    if dividir:
        spec, falhas = dividir
        citadas = ", ".join(f"#{n}" for n in falhas)
        fecha = " ".join(f"Closes #{n}" for n in falhas)
        return (
            f"A tarefa desta sessão é dividir {_relativo(spec, raiz)}: ela teve "
            f"tentativa fechada pelo guardião ({citadas}). Leia a issue, divida a "
            "spec em partes menores (cada parte já revisada), marque a original "
            "como `draft`, diga nela para onde foi cada parte e ponha no corpo do "
            f"PR: {fecha}. Não toque em nenhuma outra spec."
        )
    fila = fila_da_revisao(prontas)
    if not fila:
        return ""
    return (
        f"A spec a revisar nesta sessão é {_relativo(fila[0], raiz)}. Não toque "
        "em nenhuma outra spec."
    )


def alvo_do_especificador(
    prontas: list[Path], prs: list[dict[str, Any]], raiz: Path | None = None
) -> str:
    travado = pr_travado(ESPECIFICACAO, prs)
    if travado:
        return _destravar(travado)
    if _com_pr(ESPECIFICACAO, prs) or len(prontas) > FILA_PARA_ESPECIFICAR:
        return ""
    return (
        f"A fila tem {len(prontas)} spec(s) ready. Para a spec nova desta "
        f"sessão, use o número {proximo_numero(raiz)}: ele está reservado para ela."
    )


def desde_a_ultima_verificacao(raiz: Path | None = None) -> datetime:
    """Hora do último relatório do Verificador, limitada à janela de 24 h."""
    agora = datetime.now(timezone.utc)
    piso = agora - JANELA_DA_VERIFICACAO
    pasta = (raiz or Path.cwd()) / PASTA_VERIFICACAO / "relatorios"
    datas = []
    if pasta.is_dir():
        for p in pasta.glob("*.md"):
            m = RELATORIO.search(p.name)
            if m:
                datas.append(datetime(*map(int, m.groups()), tzinfo=timezone.utc))
    return max([piso, *datas])


def alvo_do_verificador(merges: list[str], prs: list[dict[str, Any]]) -> str:
    """`merges`: títulos do que a raia de desenvolvimento levou à main no período."""
    travado = pr_travado(VERIFICACAO, prs)
    if travado:
        return _destravar(travado)
    if _com_pr(VERIFICACAO, prs) or not merges:
        return ""
    return "Verifique o que estes merges levaram à main: " + "; ".join(merges) + "."


def entregas_sem_spec(titulos: list[str]) -> int:
    """Quantas entregas seguidas da raia de desenvolvimento não fecharam spec.

    `titulos` vem do mais novo para o mais antigo. PR de outra raia não conta
    nem interrompe a contagem.
    """
    n = 0
    for titulo in titulos:
        if raia_do_titulo(titulo) != DESENVOLVIMENTO:
            continue
        if ENTREGA_DE_SPEC.match(titulo.strip()):
            break
        n += 1
    return n


def decidir(
    prontas: list[Path],
    issues: list[dict[str, Any]],
    prs: list[dict[str, Any]],
    producao_quebrada: bool = False,
    titulos_da_main: list[str] | None = None,
    raiz: Path | None = None,
) -> Papel:
    """O papel da sessão que ninguém nomeou (decisão pura, testável).

    O desenvolvedor vem primeiro sempre que tem trabalho de produto. Sem ele,
    a sessão assume a raia que segura a fila: revisão antes de especificação,
    porque spec escrita e não revisada ainda não é trabalho para ninguém.
    """
    motivo = trabalho_do_desenvolvimento(prontas, issues, prs, producao_quebrada)
    if motivo:
        return Papel(DESENVOLVEDOR, motivo)
    alvo = alvo_do_revisor(prontas, issues, prs, raiz)
    if alvo:
        return Papel(
            REVISOR,
            "o desenvolvimento não tem trabalho de produto e a fila espera a "
            "raia de revisão.",
            alvo,
        )
    alvo = alvo_do_especificador(prontas, prs, raiz)
    if alvo:
        return Papel(
            ESPECIFICADOR,
            "o desenvolvimento não tem trabalho de produto e a fila de specs "
            "está no fim.",
            alvo,
        )
    paradas = entregas_sem_spec(titulos_da_main or [])
    if prontas and paradas >= LIMITE_SEM_SPEC:
        return Papel(
            DESENVOLVEDOR,
            f"FILA TRAVADA: há {len(prontas)} spec(s) ready e as últimas {paradas} "
            "entregas do desenvolvimento não fecharam nenhuma.",
            "A entrega desta sessão é destravar a fila, não outra melhoria: ache "
            "o que a segura (CICLO.md, *Fila travada*). Causa no repositório se "
            "corrige agora; causa fora dele vai uma única vez para a seção "
            "*Bloqueios* do estado do sistema. Com o bloqueio já registrado, "
            "encerre sem PR.",
        )
    return Papel(DESENVOLVEDOR, "")


def para_persona(
    persona: str,
    prontas: list[Path],
    issues: list[dict[str, Any]],
    prs: list[dict[str, Any]],
    merges: list[str] | None = None,
    raiz: Path | None = None,
) -> Papel:
    """O alvo da persona que a tarefa nomeou; alvo vazio = encerrar sem PR."""
    if persona == REVISOR:
        alvo = alvo_do_revisor(prontas, issues, prs, raiz)
    elif persona == ESPECIFICADOR:
        alvo = alvo_do_especificador(prontas, prs, raiz)
    elif persona == VERIFICADOR:
        alvo = alvo_do_verificador(merges or [], prs)
    else:
        raise ValueError(f"persona desconhecida: {persona}")
    return Papel(persona, "a tarefa nomeou a persona.", alvo)


def titulos_da_main(desde: datetime | None = None, limite: int = 40) -> list[str]:
    """Títulos dos commits da main, do mais novo para o mais antigo."""
    comando = ["git", "log", "origin/main", "--format=%s", f"-{limite}"]
    if desde:
        comando.append(f"--since={desde.isoformat()}")
    try:
        saida = subprocess.run(comando, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return []
    return [t for t in saida.stdout.splitlines() if t.strip()]


def merges_do_desenvolvimento(desde: datetime) -> list[str]:
    return [t for t in titulos_da_main(desde) if raia_do_titulo(t) == DESENVOLVIMENTO]


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    persona = args[0].lower() if args else ""
    if persona and persona not in RAIA_DA_PERSONA:
        print(
            f"Uso: python -m devagent.papel [{' | '.join(RAIA_DA_PERSONA)}]",
            file=sys.stderr,
        )
        return 2

    from devagent import estado_github, saude

    try:
        estado = estado_github.coletar()
    except OSError as exc:
        print(f"Falha ao consultar o GitHub: {exc}", file=sys.stderr)
        return 3
    prontas = specs_prontas()

    if persona:
        merges = (
            merges_do_desenvolvimento(desde_a_ultima_verificacao())
            if persona == VERIFICADOR
            else None
        )
        papel = para_persona(persona, prontas, estado["issues"], estado["prs"], merges)
        if not papel.alvo:
            print(
                f"Sem trabalho para o {NOME[persona]} nesta volta: encerre sem PR "
                "e sem commit."
            )
            return 0
        print(papel.alvo)
        return 0

    try:
        quebrada = bool(saude.pedem_correcao(saude.ler(espera=90)))
    except saude.Indisponivel:
        quebrada = False
    papel = decidir(
        prontas, estado["issues"], estado["prs"], quebrada, titulos_da_main()
    )
    print(f"Papel: {NOME[papel.persona]}")
    if papel.frase():
        print(papel.frase())
    return 0


if __name__ == "__main__":
    sys.exit(main())
