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
| Probabilidade de Fechamento de Gap | Dado um gap de abertura de > 2%, qual a probabilidade histórica de ele fechar no mesmo dia? (Incerteza como produto e cruzamento do próprio histórico) | yfinance | M | Médio |
| Risco de Correção do Ibov (Esticado) | Quão distante o Ibov está da sua média de 20 e histórico de regressão à média (Incerteza). | yfinance | M | Baixo |
| Relatório Dinâmico de "Hoje vs Pior Dia do Ano" | Comparação direta do clima atual com o pior pregão dos últimos 12 meses. | yfinance / brapi | P | Baixo |
| Radar de Inversão de Curva de Juros | Mostrar se os juros curtos ultrapassaram os longos e os últimos 3 vezes que isso ocorreu, como o Ibovespa reagiu nos 6 meses seguintes (Cruzamentos). | Scraping B3/yahoo | G | Alto (dificuldade de achar a fonte) |
| Sentimento de Mercado Baseado na Dispersão | Proporção de ações subindo x caindo, independentemente do peso do Ibov (Incerteza, saindo do óbvio). | brapi | P | Baixo |
| Correlação Ibovespa vs S&P500 em tempo real | Mostrar como o clima lá fora está "puxando" o Brasil (Incerteza/Cruzamento) | yfinance | M | Baixo |
| Probabilidade de nova máxima histórica no ano | Calcular chance do Ibov renovar topo usando velocidade do fluxo recente | brapi.dev / yfinance | G | Médio (Complexidade estatística) |
| Ranking de Volatilidade Absoluta | Quais papéis dão os solavancos mais fortes, independente da direção? | yfinance | P | Baixo |
| Painel de Incerteza Analítica | Onde o mercado discorda mais? Ações com maior range de preços-alvo. | CVM / Scraping | G | Alto (Scraping sensível) |
| Simulador "E se?" Histórico | Como a cesta atual se comportou no Joesley Day ou auge da pandemia | yfinance | M | Médio |
| Alerta de "Volume Oculto" Intraday | Ações onde o volume de negócios destoa do book aparente | brapi.dev | M | Baixo |

| Índice de Frustração (Pavios Superiores) | Responde: Quais ações não sustentam altas no intraday? Originalidade: Foca na anatomia do candle. | yfinance | P | Baixo |
| Sobrevivência a Quedas (Escudo) | Responde: O que costuma segurar a carteira em dias de pânico? Originalidade: Conta os dias positivos durante quedas do Ibov. | yfinance | M | Médio |
| Sensibilidade ao Dólar | Responde: Quais ações se beneficiam ou sofrem quando o dólar sobe? Originalidade: Mostra a correlação simples recente de ações vs BRL=X. | yfinance | P | Baixo |
| Tempo Médio de Recuperação (TMR) | Responde: Se cair, quanto tempo leva em média para voltar? Originalidade: Mede tempo de drawdown em vez de rentabilidade. | yfinance | G | Médio |
| Gêmeos de Comportamento | Responde: Quais ações estão andando de mãos dadas recentemente? Originalidade: Encontra os pares com maior correlação no último mês. | yfinance | M | Baixo |
| Fator Mola (Resiliência Intraday) | Identificar as ações que mais rebatem após atingirem a mínima do dia | yfinance | P | Baixo |
| Ibovespa Sombra (Equally Weighted) | Mostrar como o índice se comportaria se todas as ações tivessem o mesmo peso | yfinance | M | Baixo |
| Alerta de Distância da Média 200 | Mostrar os papéis mais esticados em relação à sua média longa | yfinance | P | Baixo |
| Volume em Leilão | Exibir papéis com atividade anormal nos leilões de abertura e fechamento | brapi | M | Alto (dificuldade na coleta do volume exato de leilão) |
| Correlação com S&P 500 Futuro | Identificar as ações locais mais sensíveis aos solavancos do índice futuro americano antes da abertura | yfinance | M | Baixo |
| Sentimento Setorial Cruzado | Agrupar os setores com maior disparidade interna (metade caindo, metade subindo) | brapi | P | Baixo |

| Experiência: Seção "Radar Intraday" | Reorganiza a página separando painéis de pulso atual dos analíticos | N/A | P | Baixo |
| Radar de Faca Caindo (Quedas Consecutivas) | Quais papéis estão derretendo há vários dias sem repique? | yfinance | P | Baixo |
| Agrupamento de Força Setorial | Mede a dispersão dentro de um mesmo setor para achar anomalias | brapi | M | Baixo |
| Variação vs IBOV (Força Relativa Diária) | Exibir o alfa diário gerado em relação ao benchmark | yfinance | P | Baixo |
| Ações "Esquecidas" (Volume sumiu) | Oportunidades em ativos que secaram de liquidez recentemente | yfinance | P | Baixo |

## Ideias (Passo 7 - 2026-10-02)


| Radar de Absorção (Defesa de Fundo) | Ações com queda semanal > 5%, mas hoje com volume anormal e repique da mínima. | yfinance | M | Baixo |
| Efeito Sexta-Feira | Probabilidade de queda na sexta para papéis que subiram forte de seg a qui. | yfinance | M | Baixo |
| Sombra do Exterior na Abertura | Descolamento do IBOV vs S&P500 Futuro nos primeiros 30 min de pregão. | yfinance | M | Médio |
