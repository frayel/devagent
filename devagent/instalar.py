"""Instala o núcleo devagent num projeto novo.

Copia a pasta devagent/ e os workflows do núcleo e cria, a partir de
devagent/modelos/, os arquivos que o projeto precisa preencher. Nunca
sobrescreve o que já existe no destino.

Uso:
    python -m devagent.instalar /caminho/do/projeto
    python -m devagent.instalar /caminho/do/projeto --dry-run

Depois: preencha PRODUTO.md e devagent.toml, ajuste o Makefile ao stack,
escreva as checagens do produto em auditoria/auditar.py (usando
devagent.auditoria.nucleo), revise os horários de auditoria-producao.yml e
auditoria-llm.yml e crie os secrets listados em devagent/OPERACAO.md.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
NUCLEO = RAIZ / "devagent"
WORKFLOWS = [
    "ci.yml",
    "automerge.yml",
    "deploy-check.yml",
    "pr-guardiao.yml",
    "jules.yml",
    "auditoria-llm.yml",
    "auditoria-producao.yml",
    "auditoria-achados.yml",
]
MODELOS = {
    "AGENTS.md": "AGENTS.md",
    "PRODUTO.md": "PRODUTO.md",
    "devagent.toml": "devagent.toml",
    "Makefile": "Makefile",
}
PASTAS_DO_PROJETO = [
    "docs/specs",
    "docs/decisions",
    "docs/runs",
    "docs/context",
    "docs/skills",
    "docs/auditoria/achados",
    "docs/auditoria/relatorios",
    "tests/fixtures",
    "auditoria",
]
ARQUIVOS_INICIAIS = {
    "docs/STATE.md": "# Estado do Sistema\n\n## Implementado\n- Nada ainda.\n",
    "docs/BACKLOG.md": "# Backlog\n\n## Correções\n\n## Ideias\n",
    "CHANGELOG.md": "# Changelog\n\n## [Unreleased]\n",
    "docs/auditoria/diario.md": "# Diário do auditor\n",
}


def ignorar(_pasta: str, nomes: list[str]) -> set[str]:
    return {n for n in nomes if n in {"__pycache__", ".pytest_cache"}}


def instalar(destino: Path, dry_run: bool = False) -> list[str]:
    feito: list[str] = []

    def copiar(origem: Path, alvo: Path) -> None:
        if alvo.exists():
            feito.append(f"mantido  {alvo.relative_to(destino)}")
            return
        feito.append(f"criado   {alvo.relative_to(destino)}")
        if dry_run:
            return
        alvo.parent.mkdir(parents=True, exist_ok=True)
        if origem.is_dir():
            shutil.copytree(origem, alvo, ignore=ignorar)
        else:
            shutil.copy2(origem, alvo)

    copiar(NUCLEO, destino / "devagent")
    for wf in WORKFLOWS:
        copiar(RAIZ / ".github" / "workflows" / wf, destino / ".github/workflows" / wf)
    for modelo, nome in MODELOS.items():
        copiar(NUCLEO / "modelos" / modelo, destino / nome)
    for pasta in PASTAS_DO_PROJETO:
        if not dry_run:
            (destino / pasta).mkdir(parents=True, exist_ok=True)
    for caminho, conteudo in ARQUIVOS_INICIAIS.items():
        alvo = destino / caminho
        if alvo.exists():
            continue
        feito.append(f"criado   {caminho}")
        if not dry_run:
            alvo.parent.mkdir(parents=True, exist_ok=True)
            alvo.write_text(conteudo, encoding="utf-8")
    return feito


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("destino", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    destino = args.destino.resolve()
    if destino == RAIZ:
        ap.error("o destino é este mesmo repositório")
    for linha in instalar(destino, args.dry_run):
        print(linha)
    print("\nPróximos passos: veja o fim da docstring de devagent/instalar.py.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
