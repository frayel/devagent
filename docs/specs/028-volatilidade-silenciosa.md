---
id: 028
titulo: Alerta de Volatilidade Silenciosa (Doji Extremo)
status: ready
esforco: M
---

## Problema
O investidor vê que o Ibovespa fechou com variação próxima a zero (ex: +0,05%) e assume que "não aconteceu nada". No entanto, pode ter havido forte oscilação intraday (máximas muito altas e mínimas muito baixas), sinalizando indecisão extrema e potencial reversão. A pergunta do usuário é: O preço não saiu do lugar, mas teve muita briga ou pouca briga hoje?

## Comportamento esperado
- Um painel na `visao-micro` intitulado "Volatilidade Silenciosa".
- A interface mostra uma lista dos 3 ativos da cesta padrão que apresentam a maior amplitude de preço (Diferença % entre a máxima e mínima do dia) e cuja variação diária entre o fechamento/cotação atual e a abertura não excede ±0,5%.
- A lista de ativos informará: Ticker, Amplitude, e Variação.

## Fontes de dados
- **URL**: `yfinance` para coleta de dados intraday ou `brapi.dev` com os campos regularMarketDayHigh, regularMarketDayLow.
- **Plano B**: Se os dados intraday não estiverem disponíveis de uma fonte para o cálculo, fallback normal de dados se possível, caso contrário o componente exibe a mensagem "Dados não disponíveis".

## Cálculos
- Amplitude %: `((Máxima - Mínima) / Mínima) * 100`
- Variação desde Abertura %: `((Cotação Atual - Abertura) / Abertura) * 100`
- Filtrar ativos onde: `Abs(Variação desde Abertura) <= 0.5%`
- Ordenar por `Amplitude %` decrescente, exibindo os top 3.

## Critérios de aceite
- [ ] O componente deve ser renderizado quando há ativos atendendo ao critério, exibindo os dados de Amplitude e Variação.
- [ ] Deve ser testado que a tabela/lista não é exibida se os dados estiverem indisponíveis e o respectivo aviso é apresentado.
- [ ] Se nenhum ativo atende ao critério de doji, um texto informando que não houve volatilidade silenciosa no pregão atual.

## Invariantes de produção
- A chave de `volatilidade_silenciosa` no `/api/snapshot` reflete adequadamente a lista de ativos, suas amplitudes e variações.
- Os cálculos são realizados considerando apenas os dados atualizados do último dia útil do pregão disponível.

## Fora do escopo
- Analisar padrões complexos de candlestick além deste filtro de doji de alto range.
- Integração em outras visões que não sejam a visao-micro.
