"""Transforma achados do auditor LLM em issues do GitHub.

O auditor LLM roda no Jules, que só entrega trabalho por PR. Ele registra cada
achado como um arquivo em docs/auditoria/achados/. Depois do merge, este
script abre uma issue para cada achado com `status: aberto` que ainda não
tenha issue (o id do achado no corpo evita duplicatas).

Severidade alta ganha o label `producao-incorreta` e entra no Passo 1 do
AGENTS.md; média e baixa viram bugs comuns, tratados no Passo 6.

Uso: python -m auditoria.achados_para_issues [--dry-run]
Precisa do gh autenticado (GH_TOKEN).
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

PASTA = Path(__file__).resolve().parent.parent / "docs" / "auditoria" / "achados"
LABELS = {
    "auditoria": ("5319E7", "Achado do auditor de produção"),
    "producao-incorreta": ("D93F0B", "Produção exibe dado errado ou está fora do ar"),
    "bug": ("D73A4A", "Algo não funciona como deveria"),
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


def ids_com_issue() -> set[str]:
    # Lê os corpos direto, sem depender do índice de busca do GitHub.
    saida = gh(
        "issue", "list", "--state", "all", "--label", "auditoria",
        "--limit", "1000", "--json", "body",
    )  # fmt: skip
    ids: set[str] = set()
    for issue in json.loads(saida or "[]"):
        ids.update(re.findall(r"<!-- achado: (\S+) -->", issue.get("body") or ""))
    return ids


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    if not args.dry_run:
        for nome, (cor, desc) in LABELS.items():
            subprocess.run(
                ["gh", "label", "create", nome, "--color", cor, "--description", desc],
                capture_output=True,
            )

    existentes = set() if args.dry_run else ids_com_issue()
    for arq in sorted(PASTA.glob("*.md")):
        if arq.name.lower() == "readme.md":
            continue
        a = ler_achado(arq)
        if not a or a.get("status", "aberto") != "aberto":
            continue
        if a["id"] in existentes:
            continue
        labels = ["auditoria", "bug"]
        if a.get("severidade") == "alta":
            labels.append("producao-incorreta")
        corpo = (
            f"{a['corpo']}\n\n---\nAchado `{a['id']}` do auditor LLM em "
            f"`docs/auditoria/achados/{a['arquivo']}` · severidade "
            f"**{a.get('severidade', '?')}** · painel `{a.get('painel', '?')}`\n\n"
            f"<!-- achado: {a['id']} -->"
        )
        titulo = f"[auditoria] {a['titulo']}"
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
