---
id: 2026-09-26-ibov-sem-dado-de-teste
severidade: alta
painel: ibovespa
status: aberto
visto_em: 2026-09-26T05:12-03:00
---

# Produção exibe dados de fixtures de teste

## O que o investidor vê
Os valores apresentados (valor `130.000` pontos e fechamentos no gráfico `[128000.0, 129000.0, 130000.5]`) correspondem à base de teste e não às métricas reais de mercado.

## O que deveria ver
Apenas os dados coletados de fontes externas como o brapi ou o fallback no Yahoo Finance, com números atualizados reais.

## Evidência
Resultado da auditoria determinística:
`ibov.sem_dado_de_teste`: valor 130.000; fechamentos [128000.0, 129000.0, 130000.5].

## Como reproduzir
Rodar `python -m auditoria.auditar --navegador`.

## Invariante proposta
A própria `ibov.sem_dado_de_teste` já cobre isso.
