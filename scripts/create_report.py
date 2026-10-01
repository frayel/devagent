import datetime
import os
import sys

if len(sys.argv) < 7:
    print(
        "Usage: python create_report.py <passo> <feito> <pr> <verificacao> <proximo> <retrospectiva>"
    )
    sys.exit(1)

passo = sys.argv[1]
feito = sys.argv[2]
pr = sys.argv[3]
verificacao = sys.argv[4]
proximo = sys.argv[5]
retrospectiva = sys.argv[6]

now = datetime.datetime.now(datetime.timezone.utc)
filename = f"docs/runs/{now.strftime('%Y-%m-%d-%H%M')}.md"
os.makedirs("docs/runs", exist_ok=True)

report_content = f"""## Passo executado
{passo}

## O que foi feito
{feito}

## PR
{pr}

## Verificação
{verificacao}

## Próximo passo provável
{proximo}

## Retrospectiva
- {retrospectiva}
"""

with open(filename, "w") as f:
    f.write(report_content)

print(f"Report created at {filename}")
