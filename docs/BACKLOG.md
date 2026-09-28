# Backlog

## Correções (prioridade sobre qualquer feature)

## Features

| Feature | Valor | Fonte de dados | Esforço (P/M/G) | Risco |
|---|---|---|---|---|
| Maiores altas e baixas do dia (tabela) | Identificar destaques diários do mercado | brapi.dev | P | Baixo (dependência de API externa) |
| Alertas de volume anormal | Detectar movimentos atípicos que precedem tendências | brapi.dev | P | Baixo (depende do cálculo sobre média histórica) |
| Médias móveis (21 e 200 dias) | Análise de tendência de curto e longo prazo | yfinance | P | Baixo |
| Calendário de Balanços | Preparação para volatilidade em datas de resultados | CVM / StatusInvest (scraping) | M | Alto (fontes instáveis ou difíceis de raspar) |
| Ficha da ação (P/L, P/VP, DY, ROE) | Análise fundamentalista rápida de uma empresa | brapi.dev | M | Médio (qualidade dos dados fundamentalistas) |
| Comparador de ações (lado a lado) | Auxilia na escolha entre pares do mesmo setor | brapi.dev | M | Médio (depende da ficha da ação) |
| Mapa de calor setorial | Visualização rápida do desempenho por setor | brapi.dev / yfinance | M | Médio (categorização correta dos setores) |
| Rastreio de carteiras recomendadas | Agregação das carteiras mensais de corretoras | Scraping (bancos/corretoras) | G | Alto (layout variável e difícil extração) |
| Fluxo do investidor estrangeiro | Entender o fluxo de capital gringo na B3 | B3 (scraping ou API não oficial) | M | Alto (fonte instável ou difícil acesso) |
| Histórico de dividendos pagos vs anunciados | Prever o fluxo de caixa do investidor focado em renda | B3 / brapi.dev | G | Alto (eventos corporativos complexos) |
| Consenso de analistas | Entender a expectativa do mercado (preço-alvo) | yfinance / scraping | G | Alto (dificuldade de extração e padronização) |
| Termômetro de sentimento | Analisar humor do mercado via notícias | Scraping (Infomoney, Valor, etc) | G | Alto (mudanças no layout dos sites, NLP) |
| Probabilidade histórica | Estudar comportamento pós-padrões | yfinance | G | Médio (complexidade de cálculo) |
| Alerta de Descolamento Setorial | Identifica se uma ação está caindo muito em dia de forte alta do seu setor | brapi.dev | P | Baixo (depende de agrupamento por setor já mapeado) |
| Calendário de Dividendos Preditivo | Prever datas de dividendos baseado no histórico anual antes do anúncio oficial | yfinance / brapi | M | Médio (eventos variam de um ano para o outro) |
| Termômetro de Risco Macro (DI, Dólar, VIX) | Indicador visual simplificado se o cenário global é de aversão ou apetite a risco | brapi.dev / Yahoo Finance | M | Alto (dificuldade em calibrar pesos dos índices) |
| Simulador Histórico de Rentabilidade vs CDI | Comparar se ter segurado o ativo superou o risco zero no período de X anos | yfinance | G | Médio (cálculo complexo de dias úteis e variação do CDI) |
| Força Relativa contra o Ibovespa | Quais ações superaram sistematicamente o Ibov nos últimos 5 ou 30 pregões | yfinance | P | Baixo |
