---
id: 005
titulo: Alertas de Volume Anormal
status: done
esforco: P
---

## Problema
O usuário deseja saber antes de todo mundo quando uma ação está sofrendo movimentações atípicas de grandes investidores institucionais. Muitas vezes um movimento de alta ou baixa de volume antecipa uma tendência (ou desastre). "Qual ação está sendo mais negociada hoje comparada ao seu padrão normal?"

## Comportamento esperado
Na página inicial (index.html), abaixo dos alertas normais e do termômetro de mercado, teremos um painel chamado "Radar de Volume Anormal". Ele listará até 5 ativos que estão apresentando volume diário consideravelmente acima da sua média móvel de volume (ex: 21 dias).
Cada item da lista exibirá o ticker, o preço atual, e o percentual de anomalia (ex: "+250% do volume normal").

## Fontes de dados
- Yahoo Finance (via `yfinance` ou httpx direto para a API spark `query1.finance.yahoo.com`), pois a brapi no plano gratuito não nos dá histórico de volume suficiente de todos ativos sem estourar quotas.
- Utilizaremos a mesma cesta das 30 ações de alta liquidez usadas para destaques e dispersão, de modo a evitar requisitar as 400+ ações da B3.
- Coleta rodando em `app.collectors.volume_alert`, agendado a cada 1 hora.
- Formato: JSON (respostas padrão do Yahoo).
- Plano B: caso Yahoo Finance caia, o painel degrada graciosamente exibindo "Dados insuficientes no momento".

## Cálculos
Para cada ticker na cesta:
1. Puxar o histórico (range=1mo, interval=1d) para obter cerca de 21 dias de pregão.
2. Calcular a média simples do volume (`Volume_Médio`) nos pregões anteriores (excluindo o pregão de hoje, se ainda aberto, para ter uma média justa de dias inteiros).
3. Pegar o `Volume_Atual` (volume acumulado hoje).
4. Calcular o ratio: `Ratio = Volume_Atual / Volume_Médio`.
5. Se `Ratio > 1.5` (50% a mais de volume) e `Volume_Médio > 0`, é um candidato.
6. Ordenar por `Ratio` decrescente, e exibir o top 5.

## Critérios de aceite
- [ ] A coleta dos dados reutiliza httpx.Client e mock via respx.
- [ ] O cálculo do Ratio ocorre com precisão, descartando divisões por zero ou dados ausentes.
- [ ] O banco de dados (`sqlite`) possui uma tabela ou cache de alertas de volume.
- [ ] A visualização mostra de forma limpa o "Ticker", "Ratio de Anomalia" e "Horário da coleta/Fonte".
- [ ] É visível o número de dias usado para a média (ex: 21 dias).

## Invariantes de produção
- Apenas ativos cujo volume de hoje supera o histórico normal em no mínimo 50% são exibidos (ou nenhum).
- Nunca quebra a home quando a fonte estiver lenta ou indisponível.
- A API `/api/snapshot` inclui o novo painel `radar_volume` seguindo o contrato padrão de auditoria de dados (nome da fonte explícito e horário do snapshot).

## Fora do escopo
- Alertas por e-mail, SMS, ou Push notification. Apenas visualização no site.
- Análise gráfica avançada intra-day (candlesticks de 5 minutos).
