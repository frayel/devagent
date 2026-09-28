"""Relógio: dispara os workflows agendados sem depender do cron do GitHub.

O cron do GitHub Actions é "melhor esforço" e, neste repositório, descarta a
maior parte dos disparos (em 2026-09-28, 5 de ~60 execuções do jules.yml).
Disparos por workflow_dispatch não são descartados. O workflow relogio.yml roda
este script a cada quarto de hora e se redispara ao terminar.

A agenda continua definida nos próprios workflows: o script lê as linhas
`- cron: "..."` de cada arquivo em .github/workflows/ e dispara, por
workflow_dispatch, os que têm horário dentro do quarto de hora atual.

Uso:
    python scripts/relogio.py                  # dispara o que está na hora
    python scripts/relogio.py --dry-run        # só mostra
    python scripts/relogio.py --em 2026-09-28T12:05:00Z --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

WORKFLOWS = Path(".github/workflows")
IGNORAR = {"relogio.yml"}  # o próprio relógio não se agenda por aqui

# Mesmo mapeamento do case em jules.yml: cron -> ação.
JULES_ACOES = {
    "*/15 * * * *": "destravar",
    "5 6 * * *": "seguranca",
    "5 12 * * *": "performance",
    "5 18 * * *": "design",
}
JULES_PADRAO = "desenvolvedor"

CRON_RE = re.compile(r'^\s*-\s*cron:\s*["\']([^"\']+)["\']')


def _campo(expr: str, valor: int, minimo: int, maximo: int) -> bool:
    for parte in expr.split(","):
        passo = 1
        if "/" in parte:
            parte, p = parte.split("/")
            passo = int(p)
        if parte == "*":
            ini, fim = minimo, maximo
        elif "-" in parte:
            a, b = parte.split("-")
            ini, fim = int(a), int(b)
        else:
            ini = fim = int(parte)
            if passo > 1:
                fim = maximo
        if ini <= valor <= fim and (valor - ini) % passo == 0:
            return True
    return False


def cron_casa(cron: str, t: datetime) -> bool:
    minuto, hora, dia, mes, semana = cron.split()
    dow = (t.weekday() + 1) % 7  # cron: 0 = domingo
    return (
        _campo(minuto, t.minute, 0, 59)
        and _campo(hora, t.hour, 0, 23)
        and _campo(dia, t.day, 1, 31)
        and _campo(mes, t.month, 1, 12)
        and (_campo(semana, dow, 0, 6) or (dow == 0 and _campo(semana, 7, 0, 7)))
    )


def inicio_do_quarto(t: datetime) -> datetime:
    return t.replace(minute=t.minute - t.minute % 15, second=0, microsecond=0)


def crons_do_quarto(cron: str, quarto: datetime) -> bool:
    return any(cron_casa(cron, quarto + timedelta(minutes=m)) for m in range(15))


def agenda(quarto: datetime) -> list[tuple[str, dict[str, str]]]:
    """Workflows (e inputs) com algum cron dentro do quarto de hora."""
    disparos: list[tuple[str, dict[str, str]]] = []
    for arquivo in sorted(WORKFLOWS.glob("*.yml")):
        if arquivo.name in IGNORAR:
            continue
        crons = [
            m.group(1)
            for linha in arquivo.read_text(encoding="utf-8").splitlines()
            if (m := CRON_RE.match(linha))
        ]
        devidos = [c for c in crons if crons_do_quarto(c, quarto)]
        if not devidos:
            continue
        if arquivo.name == "jules.yml":
            acoes = [JULES_ACOES.get(c, JULES_PADRAO) for c in devidos]
            # Um disparo só por quarto: o jules.yml tem concorrência com
            # cancelamento de pendentes, e toda ação já destrava ao final.
            principais = [a for a in acoes if a != "destravar"]
            disparos.append(
                ("jules.yml", {"acao": principais[0] if principais else "destravar"})
            )
        else:
            disparos.append((arquivo.name, {}))
    return disparos


def ja_executado(quarto: datetime) -> bool:
    """Outra execução do relógio já concluiu este quarto de hora?"""
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    atual = os.environ.get("GITHUB_RUN_ID", "")
    if not repo:
        return False
    desde = quarto.strftime("%Y-%m-%dT%H:%M:%SZ")
    saida = subprocess.run(
        [
            "gh",
            "api",
            f"repos/{repo}/actions/workflows/relogio.yml/runs"
            f"?event=workflow_dispatch&status=success&created=>={desde}",
        ],
        capture_output=True,
        text=True,
    )
    if saida.returncode != 0:
        return False
    runs = json.loads(saida.stdout).get("workflow_runs", [])
    return any(str(r["id"]) != atual for r in runs)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--em", help="instante UTC ISO para simular")
    args = ap.parse_args()

    agora = (
        datetime.fromisoformat(args.em.replace("Z", "+00:00"))
        if args.em
        else datetime.now(timezone.utc)
    )
    quarto = inicio_do_quarto(agora)
    print(f"Quarto de hora: {quarto:%Y-%m-%d %H:%M} UTC")

    if not args.dry_run and ja_executado(quarto):
        print("Este quarto de hora já foi processado por outra execução.")
        return 0

    for workflow, inputs in agenda(quarto):
        cmd = ["gh", "workflow", "run", workflow, "--ref", "main"]
        for k, v in inputs.items():
            cmd += ["-f", f"{k}={v}"]
        print("->", " ".join(cmd[3:]))
        if not args.dry_run:
            r = subprocess.run(cmd, capture_output=True, text=True)
            if r.returncode != 0:
                print(f"   falhou: {r.stderr.strip()}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
