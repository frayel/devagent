---
id: 037
titulo: Radar de Congestionamento (Estreitamento de Bandas)
status: ready
esforco: M
---

## Problema
O usuário deseja identificar ativos que estão operando em faixas de preço extremamente estreitas há vários dias, indicando acumulação de energia e potencial para um movimento forte (rompimento) em breve, mas que passam despercebidos porque não estão variando muito hoje.

## Comportamento esperado
Um novo painel "Radar de Congestionamento" na seção "Rankings & Destaques" ou "Alertas Intraday".
Exibe uma tabela com até 5 ações de alta liquidez que apresentam a menor volatilidade histórica recente (menor desvio padrão relativo ou bandas de Bollinger mais estreitas nos últimos 20 dias).
A tabela exibe o ticker, a amplitude percentual da faixa recente e um minigráfico (sparkline) reto mostrando a compressão.

## Fontes de dados
`yfinance` (endpoint spark ou histórico diário dos últimos 20 pregões para a cesta de 30 tickers de alta liquidez).
Plano B: se falhar, exibir "Dado indisponível".

## Cálculos
- Baixar o histórico diário de fechamentos dos últimos 20 pregões para as ações mais líquidas.
- Para cada ação, calcular o desvio padrão dos últimos 20 fechamentos dividido pela média móvel de 20 dias (Bandwidth das Bandas de Bollinger).
- Filtrar as 5 ações com os menores valores de Bandwidth (maior estreitamento).
- Gerar minigráfico com o histórico de fechamentos desses 20 dias para evidenciar o achatamento.

## Critérios de aceite
- [ ] verificáveis por teste automatizado: mock da API retornando dados de preços achatados e o cálculo identifica corretamente o ativo com menor volatilidade.
- [ ] O painel aparece na chave `/api/snapshot` como `radar_congestionamento`.

## Invariantes de produção
A chave `radar_congestionamento` em `/api/snapshot` retorna a lista de ativos com suas métricas, sem quebrar os outros painéis.

## Fora do escopo
Sinalizar para que lado será o rompimento (bullish ou bearish). O objetivo é apenas mostrar a compressão.
