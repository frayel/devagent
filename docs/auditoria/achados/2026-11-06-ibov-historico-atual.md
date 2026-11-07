---
id: 2026-11-06-ibov-historico-atual
severidade: alta
painel: ibovespa
status: aberto
visto_em: 2026-11-06T22:20:00-03:00
---

# Gráfico não chega ao pregão mais recente

## O que o investidor vê
O gráfico do Ibovespa mostra a última data como `2026-11-04`, deixando de refletir os dados mais recentes do mercado.

## O que deveria ver
O gráfico com o último ponto cobrindo a data de fechamento mais recente (esperado 2026-11-06).

## Evidência
Resultado da auditoria determinística:
`ibov.historico_atual`: última data 2026-11-04; pregão esperado 2026-11-06.

## Como reproduzir
Rodar `make audit ARGS="--navegador --saida /tmp/auditoria"` e observar a falha na checagem `ibov.historico_atual`.

## Invariante proposta
A própria checagem `ibov.historico_atual` já valida isso.
