# devagent · Painel B3

Dashboard de apoio à decisão para investidores da B3, construído e mantido por um agente autônomo (Google Jules) que especifica, implementa, revisa e publica o sistema em ciclos curtos.

> Conteúdo informativo gerado automaticamente. Não constitui recomendação de investimento.

## O que existe hoje

Veja [`docs/STATE.md`](docs/STATE.md). As próximas ideias ficam em [`docs/BACKLOG.md`](docs/BACKLOG.md) e as especificações em [`docs/specs/`](docs/specs/).

## Rodar localmente

```bash
python3.12 -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
python -m app.collectors.ibovespa      # coleta e grava no SQLite
uvicorn app.main:app --reload          # http://localhost:8000
```

Qualidade:

```bash
ruff check . && ruff format --check .
mypy app
pytest -q
```

## Como o agente trabalha

As instruções estão em [`AGENTS.md`](AGENTS.md). Em resumo, cada execução faz uma única coisa, na primeira situação que se aplicar:

1. corrigir produção ou testes quebrados;
2. conferir se o que foi mergeado chegou à produção;
3. tratar o PR aberto;
4. implementar a próxima spec;
5. melhorar documentação, skills e as próprias instruções;
6. tratar a issue aberta mais prioritária;
7. propor novas features e escrever a próxima spec.

Para pedir algo ao agente, abra uma issue. O label `prioridade` a coloca no começo da fila.

Procedimentos recorrentes ficam em [`docs/skills/`](docs/skills/) e conhecimento durável em [`docs/context/`](docs/context/). Cada execução deixa um relatório com retrospectiva em [`docs/runs/`](docs/runs/).

## Entrega

PR do agente → CI → merge automático → deploy no Render → verificação do deploy. Detalhes e variáveis necessárias em [`docs/context/operacao.md`](docs/context/operacao.md).
