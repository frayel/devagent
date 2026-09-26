# ADR 001 · Guardião de PRs e prioridade para destravar

- **Status:** aceita
- **Data:** 2026-09-26

## Contexto

Um PR do agente falhou no CI e ficou aberto. As execuções seguintes do Jules não o enxergaram (a instrução "liste os PRs" não dizia como), abriram outro PR e o primeiro nunca foi corrigido. Um humano teve de fazer o merge à mão. No mesmo período, um commit reescreveu o `AGENTS.md` a partir de uma cópia antiga e apagou o passo de tratar issues.

## Decisão

1. `scripts/estado_github.py` é o primeiro comando de toda execução e mostra PRs (CI, conflito) e issues sem precisar de token.
2. Destravar o PR aberto vira o Passo 2, logo depois de produção quebrada.
3. O workflow `pr-guardiao.yml` age mesmo se o agente não agir: cobra `@jules` com o log (até 3 vezes), fecha PRs sem reação em 3 h, com conflito grande (> 3 arquivos ou > 40 linhas) ou substituídos, e registra o motivo numa issue `tentativa-falhou`.
4. Conflito pequeno é resolvido na própria branch; conflito grande não é resolvido: o PR é fechado e o próximo ciclo refaz o trabalho sobre a `main` atual, porque a spec continua `ready` lá.
5. O guardião entra na lista de arquivos protegidos do auto-merge.

## Consequências

Nenhum PR fica aberto por mais de algumas horas sem progresso. O custo é refazer trabalho em conflitos grandes, aceito porque recriar sobre a `main` atual é mais seguro que resolver muitos conflitos às cegas.
