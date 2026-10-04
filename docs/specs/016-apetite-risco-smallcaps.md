---
id: 016
titulo: Apetite a Risco (Small Caps vs Ibov)
status: done
esforco: P
---

## Problema
O investidor vê o Ibovespa (formado por grandes empresas maduras) estável, mas não sabe se o mercado está buscando ou fugindo de risco. Medir o índice Small Caps (SMLL) em relação ao Ibovespa (BVSP) ajuda a mostrar se os investidores estão comprando crescimento/risco ou se refugiando em dividendos/segurança.

## Comportamento esperado
Um card na página inicial indicando o "Apetite a Risco" diário.
Se o índice SMLL estiver subindo mais (ou caindo menos) que o IBOV (diferença positiva), a mensagem será: "Mercado tomando risco (Small Caps superam Ibov)".
Se o IBOV estiver melhor que o SMLL, a mensagem: "Mercado defensivo (Ibov supera Small Caps)".
Exibe a diferença percentual de desempenho (ex: SMLL +1.5% e IBOV +0.5% -> Diferença +1.0%).
O card ganha a cor verde se tomando risco, e vermelho se defensivo.

## Fontes de dados
Usar o yfinance para buscar o fechamento anterior e o preço atual dos índices `^SMLL` (ou equivalente no yfinance como ETF SMAL11.SA se o índice não estiver disponível) e `^BVSP`.
Como o yfinance nem sempre tem um ticker bom para o índice SMLL em tempo real no Brasil, o plano principal usará o ETF `SMAL11.SA` como proxy do índice de small caps.

## Cálculos
1. Coletar variação percentual de `SMAL11.SA` e `^BVSP` no dia atual usando yfinance.
2. Calcular a diferença de variação: `var(SMAL) - var(IBOV)`.
3. Se a diferença for > 0, o estado é "Tomando risco". Se < 0, "Defensivo". Se próximo a 0 (-0.1 a 0.1), "Neutro".

## Critérios de aceite
- [x] Banco de dados contém a tabela `apetite_risco_cache`.
- [x] O coletor calcula a variação e determina o estado diário (Tomando risco, Defensivo, Neutro).
- [x] O contrato da API `/api/snapshot` inclui a chave `apetite_risco`.
- [x] O componente no frontend exibe o estado corretamente com base na variação.
- [x] O sistema degrada graciosamente se o yfinance falhar, mostrando estado "indisponível".

## Invariantes de produção
- A propriedade `apetite_risco` em `/api/snapshot` não deve quebrar o contrato.

## Fora do escopo
Análise histórica profunda do SMLL vs IBOV (focaremos apenas no dia atual, ou "hoje").
