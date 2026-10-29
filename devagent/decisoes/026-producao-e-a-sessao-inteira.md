# ADR 026 · Produção quebrada é a sessão inteira

- **Data:** 2026-10-29 · **Status:** aceita
- **Revê:** ADR 024 (decisão 9) e ADR 015

## Contexto

Em 28/10 a issue `producao-incorreta` #577 (o painel principal sem coleta havia 22 h) ficou 7 h aberta enquanto o desenvolvimento entregava quatro PRs sobre outros assuntos (#580, #582, #583 e #584). O relatório de uma dessas sessões dizia "há issues de produção exigindo ação" e, mesmo assim, tratava uma issue `prioridade`.

O prompt da sessão juntava duas frases que competiam:

1. o aviso de produção do ADR 024, com uma saída: "se já há correção mesclada esperando a verificação (comentário `correcao-mergeada`) e nada novo apareceu, siga para o próximo item do ciclo";
2. a frase da fila, imperativa: "o trabalho desta sessão é corrigir a #573" ou "implementar a spec X".

O agente seguia a mais imperativa, e quem decidia se a saída valia era o próprio agente, lendo os comentários.

## Decisão

1. **Quem decide se há correção mesclada é o código.** `estado_github.marcar_correcoes` lê os comentários de cada issue de produção e marca `correcao_mergeada` quando há o comentário `<!-- correcao-mergeada -->` do `automerge.yml` e nenhum sinal de falha nova depois dele (novo relatório de falhas, "A correção mergeada não resolveu", "Os problemas mudaram"). Sem acesso aos comentários, a issue conta como pendente.
2. **Com issue de produção pendente, a frase da sessão é só ela**: "o trabalho desta sessão é corrigir a #N pelo Passo 1, num PR `fix:` com `Closes #N`". Sem fila, sem issue `prioridade`, sem outra tarefa competindo.
3. Com todas as issues de produção já corrigidas e esperando a verificação, a frase diz isso e devolve a fila normal.
4. O `estado_github` passa a imprimir a instrução também quando a fila de specs está vazia mas há produção pendente.

## Consequências

- Uma sessão por vez ataca a produção quebrada até o `automerge.yml` registrar a correção. Se a correção não resolver, a auditoria comenta de novo e a issue volta a ser pendente na rodada seguinte.
- A leitura dos comentários custa uma chamada à API por issue de produção aberta; normalmente são uma ou duas.
