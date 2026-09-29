# devagent · Painel B3

Dashboard de apoio à decisão para investidores da B3, construído e mantido por um agente autônomo (Google Jules) que especifica, implementa, revisa e publica o sistema em ciclos curtos.

> Conteúdo informativo gerado automaticamente. Não constitui recomendação de investimento.

## O que existe hoje

Veja [`docs/STATE.md`](docs/STATE.md). As próximas ideias ficam em [`docs/BACKLOG.md`](docs/BACKLOG.md) e as especificações em [`docs/specs/`](docs/specs/).

## Rodar localmente

```bash
python3.12 -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
python -m app.collectors.ibovespa      # coleta e grava no SQLite (data.db por padrão, configurável via DATABASE_PATH)
uvicorn app.main:app --reload          # http://localhost:8000
```

Qualidade (os mesmos alvos que o CI roda):

```bash
make verify        # lint, tipos e testes
make smoke         # sobe a app com o comando do render.yaml e confere /healthz
make audit         # audita produção
```

## Como o agente trabalha

O agente tem duas camadas de instruções, lidas a partir do [`AGENTS.md`](AGENTS.md):

- [`devagent/`](devagent/README.md) é o **núcleo**: o ciclo de decisão ([`devagent/CICLO.md`](devagent/CICLO.md)), as personas, as skills de processo, o guardião de PRs, os adaptadores do Jules e do Render e o harness da auditoria. Não conhece o produto (um teste garante) e pode ser levado a outro projeto com `python -m devagent.instalar <destino>`.
- [`PRODUTO.md`](PRODUTO.md) é o **projeto**: o painel, o stack, as regras de coleta e o índice da documentação deste produto.

Os dois vivem no mesmo repositório para que o agente continue aprimorando o núcleo. Em resumo, cada execução faz uma única coisa, na primeira situação que se aplicar:

1. corrigir produção ou testes quebrados;
2. destravar o PR aberto (CI falhando, conflito, revisão);
3. conferir se o que foi mergeado chegou à produção;
4. implementar a próxima spec;
5. melhorar documentação, skills e as próprias instruções;
6. tratar a issue aberta mais prioritária;
7. propor novas features e escrever a próxima spec.

Para pedir algo ao agente, abra uma issue. O label `prioridade` faz o agente tratá-la no Passo 1, antes de specs e features; sem o label, ela espera na fila do Passo 6. Defeitos conhecidos também podem ser registrados na seção *Correções* de `docs/BACKLOG.md`, que entra no mesmo Passo 1.

Nenhum PR fica parado: o guardião (`pr-guardiao.yml`) cobra o Jules quando o CI falha e, sem reação, fecha o PR e registra o motivo para o próximo ciclo refazer o trabalho.

Procedimentos recorrentes ficam em [`devagent/skills/`](devagent/skills/) (processo) e [`docs/skills/`](docs/skills/) (produto); conhecimento durável em [`docs/context/`](docs/context/). Cada execução deixa um relatório com retrospectiva em [`docs/runs/`](docs/runs/).

## Entrega

PR do agente → CI → merge automático → deploy no Render → verificação do deploy. Detalhes e variáveis necessárias em [`devagent/OPERACAO.md`](devagent/OPERACAO.md) e na seção 10 do [`PRODUTO.md`](PRODUTO.md).
