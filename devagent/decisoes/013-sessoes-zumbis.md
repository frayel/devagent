# ADR 013 · Encerrar sessões zumbis do Jules

- **Data:** 2026-10-18 · **Status:** aceita
- **Complementa:** ADR 012

## Contexto

Em 18/10, o ciclo ficou parado das 04h31 às 13h17 (BRT), com as rodadas rodando a cada 30 min e todas com sucesso. O Sentinel abriu o PR #335 às 03h40, o CI falhou, o guardião cobrou o Jules no PR e ele corrigiu; o PR foi mesclado às 04h31. A sessão, reaberta pela cobrança, continuou "ativa" na API depois do merge. Como só uma sessão que altera código roda por vez, cada rodada encontrou essa sessão e não iniciou outra. O Bolt perdeu o dia.

O destravar só tratava sessões paradas em pergunta ou em aprovação de plano. Uma sessão `IN_PROGRESS` ou `PAUSED` que não trabalhava mais não tinha quem a encerrasse.

## Decisão

A cada rodada, antes de escolher a próxima persona, o adaptador encerra (mensagem de encerramento e `DELETE`) toda sessão ativa do repositório que:

1. tem PR já mesclado ou fechado: o trabalho dela acabou; ou
2. está há 3 h ou mais sem atualização (`updateTime`). A mediana de uma sessão até o PR é ~30 min.

O `iniciar` também ignora essas sessões na trava de "sessão ativa", para que uma falha no encerramento não volte a travar a fila.

## Consequências

- O pior caso de trava cai de indefinido para 3 h, e o caso de 18/10 (PR mesclado) se resolve na rodada seguinte ao merge, em até 5 min.
- Uma sessão legítima que passe 3 h sem atualizar é encerrada. O PR dela, se existir, continua sob o guardião, e o desenvolvedor a destrava pelo Passo 2.
