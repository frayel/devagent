---
id: 2026-09-26-ibov-historico-tamanho
severidade: alta
painel: ibovespa
status: aberto
visto_em: 2026-09-26T05:12-03:00
---

# Gráfico do Ibovespa com poucos pregões

## O que o investidor vê
O gráfico exibido na página possui poucos pregões, mostrando apenas os últimos 3 pregões, o que contraria as expectativas de ter um escopo maior (ao menos 15).

## O que deveria ver
Um gráfico histórico com uma janela contendo pregões suficientes, com um mínimo de 15 pregões plotados.

## Evidência
Resultado da auditoria determinística:
`ibov.historico_tamanho`: 3 pregões (mínimo 15).

## Como reproduzir
Rodar `python -m auditoria.auditar --navegador`.

## Invariante proposta
A própria `ibov.historico_tamanho` já trata disso.
