---
id: 2026-11-03-mare-calma-zerada
severidade: media
painel: mare
status: resolvido
visto_em: 2026-11-03T04:20:00-03:00
pr: 691
---

# Maré do mercado exibe componente Calma com valor 0, contrariando o histórico e o esperado

## O que acontece
No painel "Maré do mercado", o componente "Calma" exibe o valor `0.0`, e a barra gráfica correspondente não é preenchida.

## O que deveria acontecer
O valor do componente Calma deve ser `100 - percentil da volatilidade de queda de 10 pregões do Ibovespa nos 252 anteriores`. A spec determina "Zero significa que a volatilidade atual de queda é a mais alta de toda a janela". O histórico retornou menos pregões que o necessário (`MINIMO_PERCENTIL` = 120), causando erros ou valores espúrios. A Maré do Mercado não deveria zerar o valor ou exibir o defeito, e o PR 691 ao invés de expor o erro no design, deveria ter tratado o defeito na coleta de volatilidade de quedas.

## Evidência
No `api/snapshot`:
```json
  "componentes": {
    "fluxo": 40.8,
    "calma": 0.0,
    "volume": 44.3
  }
```

## Como reproduzir
1. Chame `/api/snapshot` e verifique o valor de `paineis.mare.componentes.calma`.
2. Acesse a rota inicial e inspecione as barras que acompanham o componente Calma.
