---
id: 2026-09-26-ibov-confere-com-fonte
severidade: alta
painel: ibovespa
status: aberto
visto_em: 2026-09-26T05:12-03:00
---

# Valor exibido não confere com a fonte

## O que o investidor vê
O investidor vê o Ibovespa a `130.000` pontos, enquanto a fonte `Yahoo Finance (^BVSP)` indica um fechamento de `183.476,86`.

## O que deveria ver
Um valor que acompanhe fielmente as fontes de mercado com margem de diferença muito pequena (menor que 1.5%).

## Evidência
Resultado da auditoria determinística:
`ibov.confere_com_fonte`: exibido 130.000,00; referência 183.476,86; diferença 29.15% (limite 1.5%).

## Como reproduzir
Rodar `python -m auditoria.auditar --navegador`.

## Invariante proposta
A própria `ibov.confere_com_fonte` verifica a diferença.
