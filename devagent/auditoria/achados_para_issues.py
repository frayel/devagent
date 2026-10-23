"""Transforma achados do auditor LLM em issues do GitHub.

O auditor LLM roda no Jules, que só entrega trabalho por PR. Ele registra cada
achado como um arquivo em docs/auditoria/achados/. Depois do merge, este
script abre uma issue para cada achado com `status: aberto` que ainda não
tenha issue (o id do achado no corpo evita duplicatas).

Severidade alta ganha o label `producao-incorreta` e entra no Passo 1 do
devagent/CICLO.md. Média e baixa ganham `prioridade` e entram no Passo 1.6,
antes da fila de specs: no Passo 6 elas esperavam a fila esvaziar, o que não
acontece enquanto o agente escreve specs (ADR 020).

O verificador geral (raia de verificação, ADR 021) usa o mesmo caminho com
`--origem verificacao`: achados em docs/verificacao/achados/, label
`verificacao`. Severidade alta e média ganham `prioridade`; baixa fica para o
Passo 6, sem furar a fila.

Uso: python -m devagent.auditoria.achados_para_issues [--origem auditoria|verificacao] [--dry-run]
Precisa do gh autenticado (GH_TOKEN).
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
PASTA = RAIZ / "docs" / "auditoria" / "achados"
LABELS = {
    "auditoria": ("5319E7", "Achado do auditor de produção"),
    "verificacao": ("1D76DB", "Achado do verificador geral (raia de verificação)"),
    "producao-incorreta": ("D93F0B", "Produção exibe dado errado ou está fora do ar"),
    "bug": ("D73A4A", "Algo não funciona como deveria"),
    "prioridade": ("B60205", "Correção que passa na frente da fila de specs"),
}


def ler_achado(arq: Path) -> dict[str, str] | None:
    texto = arq.read_text(encoding="utf-8")
    m = re.match(r"---\n(.*?)\n---\n(.*)", texto, re.DOTALL)
    if not m:
        return None
    meta = dict(
        (k.strip(), v.strip())
        for k, v in (
            linha.split(":", 1) for linha in m.group(1).splitlines() if ":" in linha
        )
    )
    corpo = m.group(2).strip()
    titulo = next(
        (ln[2:].strip() for ln in corpo.splitlines() if ln.startswith("# ")), arq.stem
    )
    meta.update(corpo=corpo, titulo=titulo, arquivo=arq.name)
    meta.setdefault("id", arq.stem)
    return meta


def gh(*args: str) -> str:
    return subprocess.run(
        ["gh", *args], check=True, capture_output=True, text=True
    ).stdout


ORIGENS = {
    "auditoria": {
        "relativo": "docs/auditoria/achados",
        "rotulo": "auditor LLM",
        "titulo": "[auditoria]",
    },
    "verificacao": {
        "relativo": "docs/verificacao/achados",
        "rotulo": "verificador geral",
        "titulo": "[verificação]",
    },
}


def labels_do_achado(origem: str, severidade: str) -> list[str]:
    labels = [origem, "bug"]
    if origem == "auditoria":
        labels.append("producao-incorreta" if severidade == "alta" else "prioridade")
    elif severidade in ("alta", "media"):
        labels.append("prioridade")
    return labels


def ids_com_issue(origem: str = "auditoria") -> set[str]:
    # Lê os corpos direto, sem depender do índice de busca do GitHub.
    saida = gh(
        "issue", "list", "--state", "all", "--label", origem,
        "--limit", "1000", "--json", "body",
    )  # fmt: skip
    ids: set[str] = set()
    for issue in json.loads(saida or "[]"):
        ids.update(re.findall(r"<!-- achado: (\S+) -->", issue.get("body") or ""))
    return ids


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--origem", choices=sorted(ORIGENS), default="auditoria")
    args = ap.parse_args(argv)
    origem = ORIGENS[args.origem]
    # PASTA é lida aqui, e não na tabela, para os testes poderem trocá-la.
    pasta = PASTA if args.origem == "auditoria" else RAIZ / origem["relativo"]

    if not args.dry_run:
        for nome, (cor, desc) in LABELS.items():
            subprocess.run(
                ["gh", "label", "create", nome, "--color", cor, "--description", desc],
                capture_output=True,
            )

    existentes = set() if args.dry_run else ids_com_issue(args.origem)
    for arq in sorted(pasta.glob("*.md")):
        if arq.name.lower() == "readme.md":
            continue
        a = ler_achado(arq)
        if not a or a.get("status", "aberto") != "aberto":
            continue
        if a["id"] in existentes:
            continue
        labels = labels_do_achado(args.origem, a.get("severidade", ""))
        relativo = origem["relativo"]
        corpo = (
            f"{a['corpo']}\n\n---\nAchado `{a['id']}` do {origem['rotulo']} em "
            f"`{relativo}/{a['arquivo']}` · severidade "
            f"**{a.get('severidade', '?')}** · painel `{a.get('painel', '?')}`\n\n"
            f"<!-- achado: {a['id']} -->"
        )
        titulo = f"{origem['titulo']} {a['titulo']}"
        if args.dry_run:
            print(f"abriria: {titulo} {labels}")
            continue
        cmd = ["issue", "create", "--title", titulo, "--body", corpo]
        for lb in labels:
            cmd += ["--label", lb]
        print(gh(*cmd).strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
