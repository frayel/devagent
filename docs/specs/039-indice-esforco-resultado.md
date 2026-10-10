---
id: 039
titulo: Índice de Esforço vs Resultado
status: ready
esforco: M
---

## Problema
O usuário quer saber onde o mercado está "brigando" muito sem sair do lugar. Qual ação teve volume gigantesco de negócios hoje (muito esforço), mas o preço ficou travado (pouco resultado), indicando que grandes players estão absorvendo ordens passivamente, sinalizando uma possível exaustão ou mudança iminente de direção.

## Comportamento esperado
Adicionar um painel na seção "Alertas Intraday" quando houver ações demonstrando alta anomalia de esforço vs resultado.
Exibe uma tabela contendo: Ticker, Aumento do Volume (x vezes a média), e Variação diária do preço (%, próxima de zero).
Se nenhum papel se encaixar, o painel não aparece.

## Fontes de dados
`yfinance` (endpoint spark) buscando dados intraday recentes (diário atual e últimas semanas) para as ações de alta liquidez.
Plano B: se falhar, o painel não é exibido.

## Cálculos
- Baixar a cotação diária e o volume atual via yfinance (`period='1mo'`).
- Para cada ação, calcular a média diária de volume dos últimos 20 pregões.
- Verificar se o volume de hoje já supera consideravelmente a média (ex: > 1.5x a média) E se a amplitude entre a abertura e o atual (corpo do candle) é mínima (ex: <= 0.5% de variação).
- Retornar o top 3 de ações com maior volume relativo que respeitam a variação estreita.

## Critérios de aceite
- [ ] Teste automatizado de coletor mockado retorna a anomalia correta com aumento do volume e corpo de candle achatado.
- [ ] A chave `/api/snapshot` é exposta sem quebrar a tela caso a lista esteja vazia.

## Invariantes de produção
A chave `esforco_resultado` em `/api/snapshot` expõe a lista calculada e não exibe valores de erro se os dados não baterem (vaza lista vazia).

## Fora do escopo
Fazer previsões se a absorção resultará em alta ou baixa. O alerta aponta apenas a ocorrência da anomalia de volume vs preço.
