"""Fila de specs prontas: qual é a próxima a implementar (CICLO.md, Passo 4).

A ordem não fica a cargo da leitura do agente. O vigia põe a próxima spec no
prompt da sessão e o `estado_github` a repete no primeiro comando, para que
nenhuma sessão escreva spec nova (Passo 7) enquanto a fila não estiver vazia
(ADR 015).

Com as raias (ADR 021), a fila tem duas metades. Spec a partir de
`revisao_obrigatoria_desde` ([disciplina] do devagent.toml) só vai para o
desenvolvimento depois que o revisor a marca com `revisada:`; antes disso ela
é trabalho da raia de revisão. Assim as duas raias nunca mexem na mesma spec.

Uso:
    python -m devagent.fila_specs     # lista as specs `ready` em ordem
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

from devagent.conferir_pr import documentos, ordem_de, status_de
from devagent.config import CONFIG
from devagent.raias import revisada

NUMERO = re.compile(r"0*(\d+)([a-z]*)")
LABEL_TENTATIVA = "tentativa-falhou"
LABEL_PRIORIDADE = "prioridade"


def chave(caminho: Path) -> tuple[int, str, str]:
    """Ordem natural: 068a < 068b < 069 < 080 < 100."""
    m = NUMERO.match(caminho.name)
    if not m:
        return (sys.maxsize, "", caminho.name)
    return (int(m.group(1)), m.group(2), caminho.name)


def specs_prontas(raiz: Path | None = None) -> list[Path]:
    """Specs com `status: ready`, da próxima a implementar para a última."""
    raiz = raiz or Path.cwd()
    pasta = raiz / documentos()["specs"]
    if not pasta.is_dir():
        return []
    prontas = [
        p
        for p in pasta.glob("*.md")
        if status_de(p.read_text(encoding="utf-8")) == "ready"
    ]
    return sorted(prontas, key=chave)


def revisao_desde() -> str:
    return str(CONFIG.get("disciplina", {}).get("revisao_obrigatoria_desde", ""))


def precisa_revisao(spec: Path, desde: str | None = None) -> bool:
    """Spec `ready` que ainda espera o revisor antes de ser implementada."""
    desde = revisao_desde() if desde is None else desde
    if not desde or ordem_de(spec.name.split("-")[0]) < ordem_de(desde):
        return False
    return not revisada(spec.read_text(encoding="utf-8"))


def fila_do_desenvolvimento(
    prontas: list[Path], desde: str | None = None
) -> list[Path]:
    return [p for p in prontas if not precisa_revisao(p, desde)]


def fila_da_revisao(prontas: list[Path], desde: str | None = None) -> list[Path]:
    return [p for p in prontas if precisa_revisao(p, desde)]


def proximo_numero(raiz: Path | None = None, ocupados: set[int] | None = None) -> str:
    """Próximo número de spec livre, contando as subpastas e os já reservados.

    Duas raias que escrevem spec ao mesmo tempo (a de especificação no Passo 7
    e o desenvolvimento ao transformar uma issue em spec) recebem números
    diferentes no prompt, para os arquivos nunca colidirem (ADR 021).
    """
    raiz = raiz or Path.cwd()
    pasta = raiz / documentos()["specs"]
    usados = set(ocupados or set())
    if pasta.is_dir():
        for p in pasta.rglob("*.md"):
            m = NUMERO.match(p.name)
            if m:
                usados.add(int(m.group(1)))
    n = max(usados, default=0) + 1
    return f"{n:03d}"


def tentativas_da_spec(spec: Path, issues: list[dict[str, Any]]) -> list[int]:
    """Issues `tentativa-falhou` abertas que citam a spec (ADR 018).

    Cada issue é um dict com `numero`, `titulo`, `labels` e, se houver, `corpo`.
    A spec 075 casa com "spec 075" e "075", mas não com "075a" nem com "#75".
    """
    m = NUMERO.match(spec.name)
    if not m:
        return []
    padrao = re.compile(
        rf"(?<![#\w])0*{m.group(1)}{m.group(2)}(?![a-z0-9])", re.IGNORECASE
    )
    return [
        i["numero"]
        for i in issues
        if LABEL_TENTATIVA in i.get("labels", [])
        and padrao.search(f"{i.get('titulo', '')}\n{i.get('corpo') or ''}")
    ]


def issue_prioritaria(issues: list[dict[str, Any]]) -> dict[str, Any] | None:
    """A issue `prioridade` aberta mais antiga, fora as `bloqueado` (Passo 1.6).

    Ela passa na frente da fila de specs. Sem isto, o prompt mandava
    implementar a próxima spec e o bug ficava atrás de uma fila que o próprio
    agente vai enchendo: a #418 (rodapé, 23/10) nunca seria tratada (ADR 020).
    """
    candidatas = [
        i
        for i in issues
        if LABEL_PRIORIDADE in i.get("labels", [])
        and "bloqueado" not in i.get("labels", [])
    ]
    return min(candidatas, key=lambda i: i["numero"]) if candidatas else None


def instrucao(
    prontas: list[Path],
    raiz: Path | None = None,
    issues: list[dict[str, Any]] | None = None,
) -> str:
    """Frase que diz o trabalho da sessão; vazia se não há prioridade nem fila.

    Issue `prioridade` aberta vem antes da fila (Passo 1.6, ADR 020).

    Se a próxima spec já tem tentativa fechada pelo guardião, a sessão não a
    implementa de novo: divide. Repetir a mesma spec do mesmo tamanho foi o
    laço de 21 e 22/10 (spec 075, PRs #402 e #403).
    """
    prioritaria = issue_prioritaria(issues or [])
    if prioritaria:
        depois = (
            f" A spec {prontas[0].name} fica para a sessão seguinte." if prontas else ""
        )
        return (
            f"Existe issue `prioridade` aberta: #{prioritaria['numero']} "
            f"({prioritaria['titulo']}). Ela vem antes da fila de specs (Passo 1.6): "
            "depois do Passo 1 (produção quebrada) e do Passo 2 (PR aberto do "
            "agente), o trabalho desta sessão é corrigi-la num PR `fix:` com "
            f"`Closes #{prioritaria['numero']}`, com teste de regressão. Não "
            f"implemente spec nesta sessão.{depois}"
        )
    if not prontas:
        return ""
    em_revisao = fila_da_revisao(prontas)
    prontas = fila_do_desenvolvimento(prontas)
    if not prontas:
        return (
            f"As {len(em_revisao)} spec(s) ready da fila ainda esperam a raia de "
            f"revisão (a próxima é {em_revisao[0].name}). Não as implemente nem "
            "as edite, e não escreva spec nova pelo Passo 7: esse passo é da raia "
            "de especificação. Depois dos Passos 1 e 2, siga para os Passos 5 e 6; "
            "se nenhum gerar entrega, encerre sem PR."
        )
    raiz = raiz or Path.cwd()
    try:
        proxima = prontas[0].relative_to(raiz)
    except ValueError:
        proxima = prontas[0]
    falhas = tentativas_da_spec(prontas[0], issues or [])
    if falhas:
        citadas = ", ".join(f"#{n}" for n in falhas)
        return (
            f"A próxima spec da fila é {proxima.as_posix()}, mas ela já teve "
            f"tentativa fechada pelo guardião ({citadas}). Não a implemente de novo "
            "do mesmo tamanho: depois dos Passos 1 e 2, leia a issue, divida a spec "
            "em specs menores pelo Passo 4 (contando os testes que serão tocados), "
            "marque a original como `draft`, ponha `Closes` para essa issue no PR e "
            "encerre. A implementação fica para a próxima sessão."
        )
    return (
        f"A fila tem {len(prontas)} spec(s) ready e revisada(s); a próxima é "
        f"{proxima.as_posix()}. Depois do Passo 1 (produção quebrada, correções, "
        "issue prioridade) e do Passo 2 (PR aberto do agente), o trabalho desta "
        "sessão é implementar essa spec pelo Passo 4: não escreva spec nova pelo "
        "Passo 7 (é da raia de especificação) e não edite specs que ainda esperam "
        "revisão. Se a spec for grande demais, divida-a como manda o Passo 4."
    )


def main() -> int:
    prontas = specs_prontas()
    if not prontas:
        print("Nenhuma spec ready.")
        return 0
    for p in prontas:
        print(p.as_posix())
    return 0


if __name__ == "__main__":
    sys.exit(main())
