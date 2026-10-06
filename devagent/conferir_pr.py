"""Confere a disciplina do ciclo num PR, sem depender da memória do agente.

Roda no CI (job `disciplina` do ci.yml) e pode rodar antes de abrir o PR:
    python -m devagent.conferir_pr [--base REF]

Compara a árvore de trabalho com o ponto em que a branch saiu da base
(padrão: origin/<GITHUB_BASE_REF> ou origin/main). Sem a base disponível,
só as regras que olham a árvore inteira rodam.

Regras (mantenha em sincronia com devagent/CICLO.md, Passos 1 e 4):
    1. Nenhuma spec fica `in-progress`. O status existe enquanto o agente
       trabalha; o PR leva a spec como `done` (ou não a toca).
    2. Arquivo de teste (`test_*.py`, `*_test.py`) só dentro de uma pasta
       `tests/`. Script de exploração não é versionado.
    3. Spec que vira `done` traz, no mesmo PR, o CHANGELOG (citando o número
       da spec) e o arquivo de estado do sistema.
    4. Correções antes de specs: um PR que começa e fecha uma spec enquanto a
       seção Correções do backlog tem entrada pendente precisa resolver uma
       dessas entradas (removê-la). Entradas que citam `bloqueado` não contam.
       Fechar uma spec que já estava `in-progress` na base é continuidade e
       não entra nesta regra.

Uma regra nunca é afrouxada no mesmo PR que corrige o que ela aponta
(README do núcleo, separação de poderes).
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from devagent.config import CONFIG

PADRAO_DOCUMENTOS = {
    "specs": "docs/specs",
    "backlog": "docs/BACKLOG.md",
    "changelog": "CHANGELOG.md",
    "estado": "docs/STATE.md",
    "secao_correcoes": "Correções",
}

STATUS = re.compile(r"^status:\s*([\w-]+)\s*$", re.MULTILINE)
ID = re.compile(r"^id:\s*0*(\d+)\s*$", re.MULTILINE)
TESTE = re.compile(r"(^test_.*|.*_test)\.py$")


@dataclass
class Resultado:
    falhas: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)

    def falha(self, texto: str) -> None:
        self.falhas.append(texto)


def documentos() -> dict[str, str]:
    return {**PADRAO_DOCUMENTOS, **CONFIG.get("disciplina", {})}


def git(*args: str, raiz: Path) -> str | None:
    r = subprocess.run(
        ["git", *args], cwd=raiz, capture_output=True, text=True, check=False
    )
    return r.stdout if r.returncode == 0 else None


def status_de(texto: str | None) -> str | None:
    if texto is None:
        return None
    m = STATUS.search(texto)
    return m.group(1) if m else None


def id_de(texto: str, caminho: str) -> str:
    m = ID.search(texto)
    if m:
        return m.group(1)
    num = re.match(r"0*(\d+)", Path(caminho).name)
    return num.group(1) if num else Path(caminho).stem


def entradas_correcoes(texto: str | None, secao: str) -> list[str]:
    """Itens de primeiro nível da seção Correções, sem os que citam bloqueio."""
    if not texto:
        return []
    dentro = False
    itens: list[str] = []
    for linha in texto.splitlines():
        if linha.startswith("## "):
            dentro = linha[3:].strip().lower().startswith(secao.lower())
            continue
        if dentro and linha.startswith("- "):
            itens.append(linha.strip())
    return [i for i in itens if "bloqueado" not in i.lower()]


def arquivos_versionados(raiz: Path) -> list[str]:
    saida = git("ls-files", "--cached", "--others", "--exclude-standard", raiz=raiz)
    return [linha for linha in (saida or "").splitlines() if linha]


def resolver_base(raiz: Path, base: str | None) -> str | None:
    candidatos = [base] if base else []
    alvo = os.environ.get("GITHUB_BASE_REF")
    if alvo:
        candidatos.append(f"origin/{alvo}")
    candidatos.append("origin/main")
    for ref in candidatos:
        if ref and git("rev-parse", "--verify", "--quiet", ref, raiz=raiz):
            mb = git("merge-base", "HEAD", ref, raiz=raiz)
            if mb:
                return mb.strip()
    return None


def conferir(raiz: Path, base: str | None = None) -> Resultado:
    doc = documentos()
    res = Resultado()
    pasta_specs = raiz / doc["specs"]

    # Regra 1: nenhuma spec in-progress.
    specs_atuais: dict[str, str] = {}
    if pasta_specs.is_dir():
        for p in sorted(pasta_specs.glob("*.md")):
            rel = p.relative_to(raiz).as_posix()
            specs_atuais[rel] = p.read_text(encoding="utf-8")
    for rel, texto in specs_atuais.items():
        if status_de(texto) == "in-progress":
            res.falha(
                f"{rel} está `in-progress`. Termine a spec e marque `done` neste "
                "PR (com CHANGELOG e estado do sistema) ou devolva para `ready`."
            )

    # Regra 2: testes só dentro de tests/.
    for caminho in arquivos_versionados(raiz):
        partes = Path(caminho).parts
        if TESTE.match(partes[-1]) and "tests" not in partes[:-1]:
            res.falha(
                f"{caminho} parece teste ou script de exploração fora de `tests/`. "
                "Mova para `tests/` ou apague do PR."
            )

    mb = resolver_base(raiz, base)
    if mb is None:
        res.avisos.append(
            "base não encontrada (faça fetch de origin/main): regras 3 e 4 puladas."
        )
        return res

    # Arquivos tocados desde a base: commits da branch, mudanças ainda não
    # commitadas e arquivos novos ainda fora do índice.
    alterados = set((git("diff", "--name-only", mb, raiz=raiz) or "").split())
    novos = git("ls-files", "--others", "--exclude-standard", raiz=raiz) or ""
    alterados |= set(novos.split())

    fechadas_novas: list[str] = []
    fechadas: list[tuple[str, str]] = []
    for rel, texto in specs_atuais.items():
        if status_de(texto) != "done":
            continue
        antes = status_de(git("show", f"{mb}:{rel}", raiz=raiz))
        if antes == "done":
            continue
        numero = id_de(texto, rel)
        fechadas.append((rel, numero))
        if antes != "in-progress":
            fechadas_novas.append(rel)

    # Regra 3: spec fechada leva CHANGELOG (citando o número) e estado.
    if fechadas:
        adicionadas = "\n".join(
            linha[1:]
            for linha in (
                git("diff", "-U0", mb, "--", doc["changelog"], raiz=raiz) or ""
            ).splitlines()
            if linha.startswith("+") and not linha.startswith("+++")
        )
        for rel, numero in fechadas:
            if not re.search(rf"(?<!\d)0*{numero}(?!\d)", adicionadas):
                res.falha(
                    f"{rel} virou `done`, mas o {doc['changelog']} não ganhou uma "
                    f"linha citando a spec {numero}."
                )
        if doc["estado"] not in alterados:
            nomes = ", ".join(n for _, n in fechadas)
            res.falha(
                f"Spec(s) {nomes} viraram `done`, mas {doc['estado']} não foi "
                "atualizado (o que foi implementado e o contador de painéis)."
            )

    # Regra 4: Correções antes de specs novas.
    if fechadas_novas:
        pendentes = entradas_correcoes(
            git("show", f"{mb}:{doc['backlog']}", raiz=raiz), doc["secao_correcoes"]
        )
        caminho_backlog = raiz / doc["backlog"]
        atuais = set(
            entradas_correcoes(
                caminho_backlog.read_text(encoding="utf-8")
                if caminho_backlog.exists()
                else None,
                doc["secao_correcoes"],
            )
        )
        resolvidas = [e for e in pendentes if e not in atuais]
        if pendentes and not resolvidas:
            res.falha(
                f"Este PR fecha {', '.join(fechadas_novas)}, mas a seção "
                f"{doc['secao_correcoes']} de {doc['backlog']} tem entrada pendente: "
                f"{pendentes[0][:120]}... Correções vêm antes de specs (CICLO.md, "
                "Passo 1, item 6). Trate a primeira entrada e remova-a no mesmo PR."
            )
    return res


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base", help="ref da base (padrão: origin/main)")
    ap.add_argument("--raiz", default=".", help="raiz do repositório")
    args = ap.parse_args(argv)

    res = conferir(Path(args.raiz).resolve(), args.base)
    for aviso in res.avisos:
        print(f"aviso: {aviso}")
    if res.falhas:
        print("Disciplina do ciclo: o PR não está pronto.\n")
        for f in res.falhas:
            print(f"- {f}")
        return 1
    print("Disciplina do ciclo: ok.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
