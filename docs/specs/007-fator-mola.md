---
id: 007
titulo: Fator Mola (Resiliência Intraday)
status: done
esforco: P
---

## Problema
O investidor costuma focar apenas em quem subiu mais no dia (fechamento vs. abertura). No entanto, algumas ações afundam muito no intraday e fecham com fortes recuperações em relação à sua mínima do dia. O "Fator Mola" identifica essas ações resilientes que apresentaram forte entrada de fluxo comprador nas mínimas para reverter parte ou todo o movimento de queda diária.

## Comportamento esperado
- Um card listando as 3 ações (dentre as 30 mais líquidas) que tiveram a maior diferença percentual positiva entre a Mínima do dia e o preço atual (ou fechamento).
- O valor exibido não será a variação do dia, e sim o "salto" desde a mínima (ex: "BBDC4: +3,2% desde a mínima").
- Adição da seção ao payload do `/api/snapshot`.

## Fontes de dados
- yfinance (`spark` ou `quote` da lista de liquidez).
- brapi.dev (fallback).
- Frequência: agendador do web service. Cache local SQLite em `fator_mola_cache`.
- Plano B: degradação graciosa com mensagem "Dados não disponíveis".

## Cálculos
- Para cada ação da cesta de liquidez, obter `regularMarketPrice` e `regularMarketDayLow`.
- Se o preço atual e a mínima estiverem disponíveis, calcular: `(regularMarketPrice - regularMarketDayLow) / regularMarketDayLow`.
- Ordenar decrescentemente e exibir as top 3.

## Critérios de aceite
- [ ] O card aparece na home quando existem dados.
- [ ] A formatação exibe as porcentagens no padrão brasileiro.
- [ ] Fallback lida corretamente com ausência de dados do yfinance (falha para brapi ou exibe indisponível sem quebrar).
- [ ] Testes com fixtures de valores de baixa/atual renderizam o ranking corretamente.

## Invariantes de produção
- A lista de ações deve ter entre 0 e 3 itens por seção.
- Se o painel for retornado pela API `api/snapshot`, ele DEVE ter a chave correspondente no JSON.

## Fora do escopo
- Histórico do fator mola para mais de um pregão (apenas intraday corrente).
- Gráficos intraday (apenas ranking tabular ou lista).
