---
id: 2026-09-26-ibov-historico-confere
severidade: alta
painel: ibovespa
status: aberto
visto_em: 2026-09-26T05:12-03:00
---

# Nenhuma data do gráfico existe na fonte

## O que o investidor vê
O gráfico desenhado na página utiliza datas e valores do passado remoto (datas exibidas de `2023-09-25` a `2023-09-27`), o que denota falta de aderência com a extração da fonte em tempo real.

## O que deveria ver
Um gráfico composto apenas por datas de pregões válidos e recentes conforme consultado pelo Yahoo Finance (^BVSP).

## Evidência
Resultado da auditoria determinística:
`ibov.historico_confere`: datas exibidas 2023-09-25 a 2023-09-27.

## Como reproduzir
Rodar `python -m auditoria.auditar --navegador`.

## Invariante proposta
A própria `ibov.historico_confere` verifica se as datas do gráfico batem.
