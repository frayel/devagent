---
id: 2026-10-26-ibov-variacao-implausivel
severidade: alta
painel: ibovespa
status: aberto
visto_em: 2026-10-26T21:52:14-03:00
---

# Ibovespa apresenta variação implausível de -13,88%

## O que o investidor vê
A página inicial mostra a pontuação do Ibovespa em 176.608 pontos e uma variação de -28.475 pontos, o que equivale a uma queda absurda de -13,88% em um único dia.

## O que deveria ver
Uma variação dentro dos limites normais do mercado. Um circuit breaker na B3 começa com queda de 10%, e 13,88% excederia o limite aceitável de volatilidade diária normal. O auditor limitou a variação máxima diária a ±12.0%. A queda real não condiz com essa magnitude abrupta sem que houvesse um evento catastrófico confirmado em outras fontes. O valor de fechamento anterior em produção parece ser de `205.083` (2026-10-23) para a cotação atual, mas as cotações passadas em production e as atuais parecem estar inconsistentes em magnitude comparadas às datas mais antigas e ao normal.

## Evidência
Resultado da auditoria determinística:
`❌ | ibov.variacao_plausivel Variação diária plausível | -13.88% (limite ±12.0%)`

E a conferência com Yahoo Finance (`^BVSP`) apontando queda de -13.88% confirmada na extração via `yfinance` para o ativo `^BVSP` no dia 2026-10-26 (hoje: 176608.23, ontem: 205083.00, var: -13.88%).

No entanto, o painel do site exibe perfeitamente os mesmos dados sem erro matemático:
`-28.475 (-13,88%)`

A divergência real é que um valor tão grande assim deveria ser revisado, pois a variação é validamente gerada pela base de dados/fonte (Yahoo Finance) e pode sugerir uma falha sistemática na fonte original no momento do fechamento, ou uma anomalia nos dados importados do último pregão (talvez um desdobramento ou bug na fonte yfinance para `^BVSP`).

## Como reproduzir
Executar a auditoria determinística (`make audit ARGS="--navegador"`) ou observar o painel Ibovespa em `https://devagent-vb52.onrender.com/`. E conferir os dados no yfinance.

## Invariante proposta
A própria `ibov.variacao_plausivel` já valida e aponta esta anomalia de variação implausível >12%.
