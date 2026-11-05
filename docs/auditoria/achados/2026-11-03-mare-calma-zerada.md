---
id: 2026-11-03-mare-calma-zerada
severidade: media
painel: mare
status: resolvido
visto_em: 2026-11-03T00:15-03:00
---

# Maré do mercado exibe componente Calma com valor 0, contrariando o histórico e o esperado

## O que o investidor vê
No painel "Maré do mercado", o componente "Calma" exibe o valor `0`, e a barra gráfica correspondente está desenhada quase sem preenchimento.

## O que deveria ver
O valor do componente Calma deve ser `100 - percentil da volatilidade de queda de 10 pregões do Ibovespa nos 252 anteriores`. Zero significa que a volatilidade atual de queda (o semidesvio com alvo zero) é a mais alta de toda a janela. Porém, no dia anterior a Maré subiu de 15 para 26 com uma alta de quase 13% do Ibovespa, sem grandes quedas nos retornos recentes. A alta forte não deveria zerar a Calma, conforme descrito na spec.

## Evidência
Na página (via `curl -s https://devagent-vb52.onrender.com/`):
```html
<span>Calma <span class="comp-peso num">peso 35%</span></span>
<svg class="comp-barra" ...><rect class="comp-trilho" .../><rect class="comp-valor" width="1" height="6"/></svg>
<span class="num comp-num">0</span>
```
No `api/snapshot`:
```json
  "componentes": {
    "fluxo": 37.2,
    "calma": 0.0,
    "volume": 44.3
  }
```

## Como reproduzir
1. Navegue para a página inicial (https://devagent-vb52.onrender.com/) ou faça GET na API `/api/snapshot`.
2. Verifique o valor do componente `calma` no painel da Maré.

## Invariante proposta
Verificar se o valor do componente Calma sofre quedas abruptas a zero em dias de alta forte do Ibovespa.

## Resolução
Marcado como resolvido em 2026-11-05. A auditoria de produção não acusou mais falhas, e o componente Maré está de acordo com as regras.
