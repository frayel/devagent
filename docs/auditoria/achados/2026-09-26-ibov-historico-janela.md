---
id: 2026-09-26-ibov-historico-janela
severidade: media
painel: ibovespa
status: aberto
visto_em: 2026-09-26T05:12-03:00
---

# Gráfico usa janela temporal incorreta

## O que o investidor vê
O gráfico apresenta um período incorreto, com a primeira data correspondendo a `2023-09-25`, o que indica que não abrange a janela fixa dos últimos 30 pregões de forma adequada.

## O que deveria ver
A visualização deveria cobrir estritamente a janela dos últimos 30 pregões do fechamento mais recente.

## Evidência
Resultado da auditoria determinística:
`ibov.historico_janela`: primeira data 2023-09-25.

## Como reproduzir
Rodar `python -m auditoria.auditar --navegador`.

## Invariante proposta
A própria `ibov.historico_janela` cobre isso.
