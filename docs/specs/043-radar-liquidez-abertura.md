---
id: 043
titulo: Radar de Liquidez de Abertura
status: ready
esforco: M
---

## Problema
O investidor institucional acorda com fome ou com sono? O usuário quer saber onde os tubarões (investidores com grande volume de capital) estão montando posições logo no início do pregão. O "Radar de Liquidez de Abertura" detecta onde ocorreu a maior velocidade de volume transacionado (R$/min) nos primeiros 30 minutos em relação ao histórico.

## Comportamento esperado
Adição de uma pequena tabela no painel "Alertas Intraday" (Visão Geral ou Sentimento). O painel listará os 3 ativos de alta liquidez que mais concentraram volume financeiro atípico (velocidade) logo na abertura, destacando-se na primeira hora de negociação.
- O painel exibe: Ticker, volume projetado % vs média e a variação do dia.

## Fontes de dados
- Yahoo Finance (`v8/finance/chart/{symbol}` ou `spark`) buscando `1d` ou `15m` nos primeiros minutos do mercado.
- A cesta de ativos é a lista padrão `TICKERS` usada em outros alertas do sistema.
- Fallback: se os dados falharem, o painel será exibido como indisponível sem quebrar a página.

## Cálculos
- Isolar o volume do dia atual (idealmente os primeiros "ticks" ou candles) e compará-lo com a média dos volumes dos últimos 10 dias.
- Como não temos acesso tick-a-tick em tempo real gratuito confiável, usaremos a variação do volume do dia atual (no momento da coleta) vs a média móvel de volume das últimas 2 semanas. Quando coletado antes das 11:30, qualquer ativo com > 50% de sua média *diária* inteira transacionada será alertado.
- Os 3 ativos com a maior proporção Volume Atual / Média Diária são exibidos.

## Critérios de aceite
- [ ] O banco de dados salva as taxas de volume no cache `liquidez_abertura_cache`.
- [ ] O serviço de formatação entrega uma lista limitada a 3 ativos, formatando R$ e % adequadamente.
- [ ] `make telas` funciona injetando seeds para o novo cache de dados.
- [ ] O snapshot expõe a chave correspondente sem stacktraces de erro.

## Invariantes de produção
- A chave no JSON exposto precisa conter as chaves padronizadas (`ticker`, `ratio`, etc.).
- Os valores mostrados devem estar em Pt-BR (ex: `150%`).

## Fora do escopo
Análise tick-a-tick real em granularidade de 1 minuto (devido aos limites das fontes open), o painel foca na proporção do volume do dia inteiro vs histórico recente.
