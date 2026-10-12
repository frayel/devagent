---
id: 044
titulo: Radar de Absorção Cruzada
status: ready
esforco: M
---

## Problema
Como saber se a queda brusca do mercado está sendo defendida pelos institucionais através de absorção maciça no fundo, indicando uma falha de continuidade de baixa (spring)? Os investidores muitas vezes são induzidos a vender no fundo sem perceber o volume anormal entrando passivamente.

## Comportamento esperado
Adicionar um painel em "Alertas Intraday" que mostre uma tabela com as 3 ações do IBOV com maior evidência de absorção: ativos com forte queda inicial no dia, e um volume muito acima da média ocorrendo na mínima do dia, mas cujo preço estagnou. A tabela deve mostrar o Ticker e o aumento do Volume Relativo (ex: +320%).

## Fontes de dados
- API do Yahoo Finance (`yfinance`) no endpoint intradiário `v8 chart`, para captar variações a cada 15m.
- Degradará mostrando "Dados indisponíveis" caso o fetch falhe.

## Cálculos
- Identificar ações com queda no dia > 1.5%.
- Extrair o volume do candle de mínima no período intraday.
- Comparar esse volume com a média de volume das velas de queda da última semana (para ter o 'Volume Relativo').
- Exibir os 3 maiores retornos dessa relação quando esta for > 200%.

## Critérios de aceite
- [ ] Mock local do Yahoo retornar a correta absorção, preenchendo a UI adequadamente.
- [ ] Presença no contrato em `/api/snapshot` como `radar_absorcao_cruzada`.

## Invariantes de produção
Apenas ativos que apresentam proporção maior que 2x o normal aparecerão no `/api/snapshot`.
Sem mensagens de erro expostas.

## Fora do escopo
Análise estrita do fluxo de Tape Reading puro através de agressão (Bid/Ask volume total); utilizaremos a VSA (Volume Spread Analysis) aplicada a candles intraday, por causa de restrições de coleta.
