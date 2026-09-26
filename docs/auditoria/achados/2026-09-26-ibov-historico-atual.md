---
id: 2026-09-26-ibov-historico-atual
severidade: alta
painel: ibovespa
status: aberto
visto_em: 2026-09-26T05:12-03:00
---

# Gráfico não chega ao pregão mais recente

## O que o investidor vê
O gráfico do Ibovespa mostra a última data como `2023-09-27`, deixando de refletir os dados mais recentes do mercado.

## O que deveria ver
O gráfico com o último ponto cobrindo a data de fechamento mais recente (esperado 2026-09-25).

## Evidência
Resultado da auditoria determinística:
`ibov.historico_atual`: última data 2023-09-27; pregão esperado 2026-09-25.

## Como reproduzir
Rodar `python -m auditoria.auditar --navegador`.

## Invariante proposta
A própria `ibov.historico_atual` já valida isso.
