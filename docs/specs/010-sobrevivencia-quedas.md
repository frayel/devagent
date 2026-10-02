---
id: 010
titulo: Sobrevivência a Quedas (Escudo)
status: ready
esforco: M
---

## Problema
O investidor quer saber o que costuma segurar a carteira em dias de pânico ou má performance geral do mercado. Quais ações subiram na contramão dos dias de queda do índice?

## Comportamento esperado
Um novo card analítico "Escudo contra Quedas", informando:
- O número de pregões de queda do Ibovespa no último mês (últimos 30 pregões).
- O top 3 de ações que mais vezes fecharam no positivo nesses dias específicos de queda do Ibov.

## Fontes de dados
- yfinance (`^BVSP` e os 30 tickers de alta liquidez) via spark ou endpoint individual `v8`.
- Fallback: "Dados indisponíveis".

## Cálculos
1. Pegar histórico diário (30 pregões) do IBOV e das 30 ações.
2. Identificar os índices (datas) onde IBOV teve retorno diário negativo.
3. Para cada ação, contar em quantas dessas datas ela teve retorno positivo.
4. Mostrar o Top 3 (desempate: maior retorno médio nesses dias).

## Critérios de aceite
- [ ] Lógica de cruzamento correta, baseada nas variações diárias (fechamento atual / fechamento anterior - 1).
- [ ] Snapshot retorna dados na chave `escudo_quedas`.

## Invariantes de produção
- A chave do snapshot tem o formato correto.

## Fora do escopo
- Correlacionar quedas do IBOV com juros americanos ou S&P 500.
