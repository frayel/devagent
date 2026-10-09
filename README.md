# devagent · Painel B3

**Projeto experimental.** Este repositório existe para medir até onde um agente de IA consegue desenvolver e manter um software sozinho, sem intervenção humana. O agente (Google Jules) escreve as especificações, implementa, revisa o próprio trabalho, publica em produção e corrige o que quebra. Nenhuma pessoa aprova planos, revisa PRs ou faz merge (ADR 007).

O software construído é um painel de apoio à decisão para investidores da B3. Ele é o objeto do experimento, não o objetivo.

> Conteúdo informativo gerado automaticamente. Não constitui recomendação de investimento.

## Por que este experimento

Agentes de código já resolvem bem tarefas isoladas: corrigir um bug, escrever uma função, abrir um PR a partir de uma issue. Quase sempre há uma pessoa em volta deles, decidindo o que fazer, revisando e consertando quando algo dá errado. O que ainda não se sabe é o que acontece quando essa pessoa sai da sala por semanas.

Algumas perguntas motivam o projeto:

- **Continuidade.** O agente consegue manter um rumo ao longo de centenas de execuções sem memória entre elas, apoiado só no que deixou escrito no repositório (specs, backlog, relatórios, ADRs)?
- **Autocorreção.** Quando o deploy falha, um teste quebra ou a produção mostra um número errado, ele percebe e conserta sem ninguém apontar?
- **Julgamento de produto.** Com escopo aberto (ADR 003), ele escolhe funcionalidades que fazem sentido, ou acumula telas sem direção?
- **Qualidade ao longo do tempo.** O código e a interface melhoram ou se degradam à medida que o sistema cresce?
- **Infraestrutura em volta.** Quanto do sucesso vem do modelo e quanto vem dos trilhos: CI, guardião de PRs, auditoria de produção, ciclo de decisão?

Um painel financeiro foi escolhido de propósito. Ele tem dados reais que mudam todo dia, fontes externas que falham, números que podem ser conferidos contra fontes independentes e uma interface que alguém de fato usaria. Erros aparecem rápido e são mensuráveis.

## O que pretendemos atingir

1. **Um sistema em produção construído sem mãos humanas no código.** A intervenção humana fica restrita a montar a infraestrutura inicial (contas, chaves, workflows) e a observar.
2. **Um núcleo reaproveitável.** O processo do agente vive em [`devagent/`](devagent/README.md), separado das regras do produto (ADR 005), para ser levado a outros projetos com `python -m devagent.instalar <destino>`.
3. **Evidência, não impressão.** Cada execução deixa um relatório com retrospectiva em [`docs/runs/`](docs/runs/), cada decisão de processo vira um ADR e cada falha de produção vira uma issue. O histórico do repositório é o registro do experimento.
4. **Um mapa dos limites.** Saber onde a autonomia se sustenta e onde ela quebra é tão útil quanto um painel que funcione. Cada ponto em que foi preciso mudar os trilhos (o guardião de PRs, a retomada depois de ambiente reiniciado, o relógio externo do Jules) registra um limite encontrado.

### Regras do jogo

- Pessoas não editam o código do produto. Ajustes humanos se limitam à infraestrutura do experimento e são registrados em ADRs ou no `CHANGELOG.md`.
- Pedidos ao agente entram como issues, do mesmo jeito que um usuário qualquer faria.
- Tudo o que o agente sabe sobre o projeto está no repositório. Não há instruções fora dele.

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
