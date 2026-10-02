# ADR 006 · Revisão de experiência no Passo 7

**Data:** 2026-10-01 · **Status:** aceito

## Contexto

Com o escopo aberto (ADR 003), o agente gerou e entregou ideias novas, mas o produto cresceu só por adição: cada painel novo era empilhado no fim da página, copiando o padrão visual do anterior. O dono do produto achou o visual pouco atrativo e mal aproveitado, e o agente nunca propôs mudar isso, por três motivos observados:

- o Passo 7 só produzia ideias no formato "pergunta nova, fonte de dados nova", e uma melhoria de experiência não cabia nele;
- nenhum passo obrigava a olhar a tela, então o agente não tinha evidência de que algo estava ruim;
- mudanças exigem evidência, e gosto não aparecia em relatório, issue ou CI.

## Decisão

- Nova skill `devagent/skills/rever-experiencia.md`: olhar as capturas, comparar com a referência, percorrer a página como o usuário e transformar problemas em ideias com evidência.
- Toda rodada do Passo 7 inclui ao menos uma ideia de experiência.
- **Cadência:** o `docs/STATE.md` do projeto conta os painéis, seções ou telas acrescentados desde a última revisão. Com 3, o Passo 7 faz uma revisão obrigatória e escolhe uma das ideias dela.
- O projeto indica no `PRODUTO.md` onde estão as capturas, a referência e o guia visual. O núcleo não conhece esses caminhos.

## O que não muda

O guia visual do projeto continua protegido: a revisão aplica o guia, não o substitui, e mudanças no guia vão em PR próprio, com revisão humana. Ciclos curtos, specs de até ~400 linhas e as demais regras do `CICLO.md` continuam valendo.

## Consequências

O produto passa a alternar crescimento e consolidação. O custo é uma execução a cada três painéis dedicada a reorganizar em vez de criar.
