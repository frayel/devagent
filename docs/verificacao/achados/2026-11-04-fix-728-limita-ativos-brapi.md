---
id: 2026-11-04-fix-728-limita-ativos-brapi
severidade: alta
painel: brapi
status: aberto
visto_em: 2026-11-04T05:25-03:00
pr: 728
---

# A chamada para brapi.dev limita a 10 ativos ou falha no plano atual

## O que acontece
A API brapi.dev está sendo chamada com múltiplos ativos em `/api/quote/{simbolos}` o que resulta em erro `HTTP 400` pois "Seu plano permite no máximo 1 ativo(s) por requisição".

## O que deveria acontecer
Sem spec implementada para tratar requisições em lotes ou ajuste no provedor para permitir maiores quotas, o sistema quebra devido a erro 400.

## Evidência
Issue 729: "HTTP 400 em https://brapi.dev/api/quote/PETR4,VALE3,ITUB4,BBDC4,B3SA3,ABEV3,BBDC3,RENT3,WEGE3,BBAS3?token=***&fundamental=false"

## Como reproduzir
Executar coleta usando API brapi.dev para destaques / destaques (ex. `make smoke` test).
