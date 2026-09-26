# ADR 002 · Correções prioritárias entram no Passo 1

- **Status:** aceita
- **Data:** 2026-09-26

## Contexto

O painel publicou o Ibovespa em 130.000 pontos, valor do fixture de teste (os testes gravavam no `data.db` real, o arquivo foi versionado e não existia cron job de coleta). O defeito foi registrado na seção *Correções* de `docs/BACKLOG.md`, mas o backlog só era lido no Passo 7. A spec 002 estava `ready` e passou na frente pelo Passo 4, construindo uma feature nova sobre um banco que não recebia dados. Issues com label `prioridade` tinham o mesmo problema: esperavam atrás das specs, no Passo 6.

## Decisão

1. O Passo 1 ganha o item 6, *Correções prioritárias*: depois das verificações de produção e qualidade, o agente trata a primeira entrada da seção *Correções* do backlog e, se não houver, a issue `prioridade` mais antiga.
2. Issues `prioridade` saem do Passo 6. Issues sem o label continuam lá, depois das specs.
3. A regra de continuidade não muda: com um PR do agente aberto, destravá-lo (Passo 2) vem antes de começar a correção.
4. A entrada do backlog é removida no mesmo PR `fix:` que a resolve.

## Consequências

Defeitos conhecidos e pedidos urgentes deixam de esperar o fim da fila de specs. O custo é que uma seção *Correções* longa pode atrasar features indefinidamente; ela deve conter só defeitos reais, não melhorias.
