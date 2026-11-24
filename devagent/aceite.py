"""Testes de aceite que nascem com a spec e só valem quando ela fecha (ADR 018).

Uma spec pode trazer, no mesmo PR em que é escrita, o teste que prova que foi
entregue. Enquanto ela não é `done`, o teste pula; quando o agente marca
`done`, ele passa a rodar no CI. Marcar uma spec como entregue sem entregar
reprova o CI, em vez de passar despercebido (a 074 foi fechada em 21/10 com
todas as tabelas que deveria remover ainda no código).

Uso num teste do projeto:

    from devagent.aceite import exigir_spec_done

    def test_tabelas_removidas():
        exigir_spec_done("075a")
        ...
"""

from __future__ import annotations

import re
from pathlib import Path

from devagent.config import localizar
from devagent.conferir_pr import documentos, status_de

ID = re.compile(r"^id:\s*(\S+)\s*$", re.MULTILINE)


def normalizar(spec_id: str) -> str:
    """'075a', '75a' e 'spec 075a' viram '75a'."""
    m = re.search(r"0*(\d+)([a-z]*)", spec_id.lower())
    return f"{m.group(1)}{m.group(2)}" if m else spec_id.lower()


def status_da_spec(spec_id: str, raiz: Path | None = None) -> str | None:
    """Status da spec pelo id, procurando também nas subpastas (done/)."""
    if raiz is None:
        arquivo = localizar()
        raiz = arquivo.parent if arquivo else Path.cwd()
    alvo = normalizar(spec_id)
    pasta = raiz / documentos()["specs"]
    achadas: dict[str, str] = {}
    for caminho in sorted(pasta.rglob("*.md")):
        texto = caminho.read_text(encoding="utf-8")
        m = ID.search(texto)
        candidato = m.group(1) if m else caminho.name
        if normalizar(candidato) == alvo:
            achadas[caminho.relative_to(raiz).as_posix()] = texto
    texto = escolher_spec(spec_id, achadas)
    return status_de(texto) if texto is not None else None


def escolher_spec(spec_id: str, achadas: dict[str, str]) -> str | None:
    """O texto da spec `spec_id` entre os arquivos com esse id (#1025).

    Com um arquivo só, é ele. Com o mesmo id repetido (duas sessões do
    Especificador reservaram o 194 em 23/11), a `draft` sai da escolha: a spec
    que vale é a que está na fila ou entregue. Se ainda sobra mais de uma,
    levanta ValueError: ler a primeira em ordem alfabética, como antes, fazia
    um `exigir_spec_done` pular para sempre sem aviso.
    """
    if len(achadas) <= 1:
        return next(iter(achadas.values()), None)
    validas = {c: t for c, t in achadas.items() if status_de(t) != "draft"}
    if len(validas) == 1:
        return next(iter(validas.values()))
    if not validas:
        return next(iter(achadas.values()))
    raise ValueError(
        f"spec {spec_id} repetida: {', '.join(sorted(validas))}. Renumere uma "
        "delas (regra 13 do conferir_pr)."
    )


def exigir_spec_done(spec_id: str, raiz: Path | None = None) -> None:
    """Pula o teste enquanto a spec não estiver `done`."""
    import pytest

    status = status_da_spec(spec_id, raiz)
    if status != "done":
        pytest.skip(f"spec {spec_id} ainda não está done (status: {status})")
