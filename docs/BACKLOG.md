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


## Ideias (Passo 7 - 2026-10-15)

| Ideia | Detalhes | Fonte | Esforço | Risco |
|---|---|---|---|---|
| Experiência: Fusão de Indicadores Globais | Responde: O Clima Global e Fator Peso Pesado estão ocupando muito espaço na primeira dobra? Originalidade: Condensar métricas globais e de peso num único painel estreito à esquerda ou direita, abrindo espaço para o painel de Ibovespa no centro. | N/A | P | Baixo |
| Saúde Técnica: Unificação de Consultas do yfinance (spark) | Responde: Muitos coletores chamam o yfinance separadamente para as mesmas ações (ex: PETR4, VALE3) em dados diários? Originalidade: Criar um cache intermediário de spark que consolida requisições, reduzindo chamadas repetidas. Medida: contagem de chamadas duplicadas no agendador. | yfinance | M | Médio |
| Experiência: Modo Zen (Ocultar Valores Absolutos) | Responde: O investidor fica ansioso com a pontuação variando? Originalidade: Exibir apenas as setas de variação percentual e cores, ocultando os pontos/valores absolutos até o hover. | N/A | P | Baixo |
| Radar de Resiliência de Baixa | Responde: Quem sobrevive ileso quando o Ibov afunda? Originalidade: Mostra apenas ações que subiram em todos os últimos 3 dias de queda forte (>1%) do Ibovespa. | yfinance | M | Médio |
| Poda: Limpeza de Rankings Secundários | Responde: "Atrasadas do Rally" ainda entrega valor num mercado lateral? Medida: Tempo vazio ou inócuo. | N/A | P | Baixo |
| Termômetro de Ansiedade Intraday | Responde: Quão longe a máxima intradiária ficou da abertura em média na cesta B3? | yfinance | M | Baixo |

## Ideias (Passo 7 - 2026-10-14)

| Saúde técnica: Refatorar todos os coletores para async_fetch_with_retry | Responde: Quanto tempo o agendador leva em inicialização? | N/A | G | Baixo |

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
| Agrupamento de Força Setorial | Mede a dispersão dentro de um mesmo setor para achar anomalias | brapi | M | Baixo |
| Variação vs IBOV (Força Relativa Diária) | Exibir o alfa diário gerado em relação ao benchmark | yfinance | P | Baixo |
| Ações "Esquecidas" (Volume sumiu) | Oportunidades em ativos que secaram de liquidez recentemente | yfinance | P | Baixo |


## Ideias (Passo 7 - 2026-10-12 4)

| Ideia | Detalhes | Fonte | Esforço | Risco |
|---|---|---|---|---|
| Experiência: Destaque Visual para a Maré | Responde: Consigo achar o que preciso, rápido? Evidência: O gauge da Maré é muito grande e empurra o Ibovespa visualmente, disputando peso. Mudança: Ajustar a classe e estilos do painel Maré. | N/A | P | Baixo |
| Radar de Divergência Acumulada | Responde: Quem está com o indicador de divergência estourado mas ainda não andou? Originalidade: Olha não para o último fechamento, mas para o acúmulo de alertas falsos recentes. | yfinance | M | Baixo |
| Termômetro de Estresse Cripto | Responde: A variação bruta do mercado local tem a ver com liquidações forçadas em cripto? Originalidade: Isolar picos de liquidação no mercado futuro de criptomoedas correlacionando com dumps na B3. | API Cripto | G | Alto |
| Impacto de Ajuste do Dólar | Responde: Quem costuma reagir mais ao fechamento da PTAX? Originalidade: Exclusão de ruído normal do dia e foco nos minutos que cercam a formação da PTAX. | Brapi | M | Baixo |
| Volume Institucional de Fim de Pregão | Responde: Para onde foi o dinheiro pesado nos últimos 15 min? Originalidade: Separa o volume de giro natural do volume do leilão que sinaliza intenção futura. | Brapi | G | Alto |

## Ideias (Passo 7 - 2026-10-12 3)

| Ideia | Detalhes | Fonte | Esforço | Risco |
|---|---|---|---|---|
| Radar de Absorção Cruzada | Responde: Qual ação está liderando na absorção de vendas massivas no seu setor? Originalidade: Cruzamento de volume agressivo no topo do book contra queda livre de setor. | yfinance/brapi | M | Baixo |
| Risco de Cauda (Extremos) | Responde: Quais ativos têm o maior risco escondido hoje caso o mercado inverta rápido? Originalidade: Mede a diferença entre a volatilidade média e a variação direcional atual de curto prazo. | yfinance | M | Baixo |
| Índice de Impulso Retardatário | Responde: Quem demorou a engatar alta mas agora tem volume acelerado? Originalidade: Isolamento de ralis que iniciam na segunda metade do pregão. | yfinance | P | Baixo |
| Cesta de Refúgio Intraday | Responde: Para onde o dinheiro "smart money" está correndo hoje no meio da volatilidade? Originalidade: Criação dinâmica de um mini-ETF defensivo baseado na performance das últimas duas horas. | brapi | M | Médio |
| Experiência: Heatmap Setorial Miniatura | Responde: A variação do Ibovespa reflete todo o mercado? Originalidade: Um heatmap em miniatura acoplado ao card principal para contexto imediato, sem consumir painéis inteiros. | N/A | P | Baixo |
| Correlação de Gaps (Gap Sympathy) | Responde: Um gap monstruoso de uma blue chip puxou papéis irrelevantes hoje? Originalidade: Exibe a lista de papéis "passageiros" da variação alheia na abertura. | brapi | M | Baixo |

## Ideias (Passo 7 - 2026-10-02)


| Radar de Absorção (Defesa de Fundo) | Ações com queda semanal > 5%, mas hoje com volume anormal e repique da mínima. | yfinance | M | Baixo |
| Efeito Sexta-Feira | Probabilidade de queda na sexta para papéis que subiram forte de seg a qui. | yfinance | M | Baixo |
| Sombra do Exterior na Abertura | Descolamento do IBOV vs S&P500 Futuro nos primeiros 30 min de pregão. | yfinance | M | Médio |

## Ideias (Passo 7 - 2026-10-03)

| Ações "Secando" (Alerta de Liquidez) | Responde: Quais ações estão perdendo liquidez? Originalidade: Foco no risco de iliquidez, não retorno. | yfinance | P | Baixo |
| Cripto vs Bolsa (Correlação) | Responde: Cripto protege contra queda do Ibov? Originalidade: Cruzamento inusitado para a B3. | yfinance | M | Baixo |
| Anomalia de Leilão de Fechamento | Responde: Quais papéis distorceram no fim do dia? Originalidade: Atenção ao momento institucional. | brapi/yfinance | G | Alto |
| Atrasadas do Rally (Laggards) | Responde: Quais ficaram para trás na alta recente do Ibov? Originalidade: Busca beta distorcido negativo. | yfinance | M | Baixo |
| Abertura Explosiva (Gaps Constantes) | Responde: Quais ações dão saltos grandes logo na abertura? Originalidade: Isola retorno open vs close-D1. | yfinance | M | Baixo |
| Experiência: Visão "Só Anomalias" | Responde: Consigo ver só alertas escondendo ruído? Originalidade: Filtro analítico de tela cheia. | N/A | P | Baixo |

## Ideias (Passo 7 - 2026-10-04)

| Concentração de Ganhos do Ibovespa | Responde: A alta do Ibov é generalizada ou puxada por 2 ações? Originalidade: Quebra o IBOV em contribuição de pontos, evidenciando fragilidade do movimento. | yfinance / brapi | M | Baixo |
| Apetite a Risco (Small Caps vs Ibov) | Responde: O investidor está tomando risco ou buscando segurança hoje? Originalidade: Usa a força relativa do índice SMLL vs BVSP intraday. | yfinance | P | Baixo |
| Anomalia de Correlação Setorial | Responde: Quais ações estão indo contra seu próprio setor agora? Originalidade: Quebra de padrão no intraday cruzado com dados setoriais. | brapi/yfinance | M | Médio (requer mapear setores) |
| Pressão de Venda a Descoberto | Responde: Quais ações estão sofrendo ataques de short sellers? Originalidade: Uso das taxas de aluguel (BTC) como indicador de sentimento negativo. | B3 (scraping) | G | Alto (difícil extração) |
| Experiência: Drill-down de Ação (Raio-X) | Responde: Como ver todos os alertas de um único ticker que chamou atenção? Originalidade: Foge da visão macro para micro sob demanda, sem trocar de página (HTMX). | N/A | M | Baixo |

## Ideias (Passo 7 - 2026-10-04 2)

| Fadiga de Tendência (Divergência RSI) | Responde: A alta dessa ação está perdendo força antes de reverter? | yfinance | M | Baixo |
| Defesa em Dias de Pânico | Responde: Quem está segurando a bronca quando o IBOV derrete hoje? | yfinance | P | Baixo |
| Resiliência Pós-Abertura | Responde: Quais ações abriram caindo, mas já viraram o jogo? | yfinance | P | Baixo |
| Anatomia do Candle (Pavios Superiores) | Responde: Quais papéis tentaram subir mas tomaram paulada (venda)? | yfinance | P | Baixo |
| Alerta de Sobrevenda Relativa | Responde: O IBOV subiu a semana toda, quem ficou esquecido? | yfinance | M | Baixo |
| Experiência: Modo "Leilão" | Como ver os movimentos do leilão de fechamento sem ruído? | N/A | M | Baixo |

## Ideias (Passo 7 - 2026-10-04 3)

| Alerta de Variação Súbita (Flash Movements) | Responde: Algum papel disparou ou derreteu nos últimos 15 minutos? Originalidade: Foca na aceleração intraday e não no retorno do dia. | yfinance | M | Médio |
| Amplitude de Tendência (Breadth) | Responde: A alta do Ibov é generalizada ou puxada por pesos pesados? Originalidade: Exibe a proporção do mercado acima da MM21 vs IBOV. | yfinance | M | Baixo |
| Modo "Só Sinais" (Experiência) | Responde: Como ver rapidamente se o mercado está verde ou vermelho no celular, sem gráficos? Originalidade: Redesign radical focado na tomada de decisão em 5 segundos. | N/A | P | Baixo |
| Mapa de Correlação Intraday | Responde: Quando o IBOV cai hoje, o que está subindo consistentemente junto? Originalidade: Foco intraday no beta invertido, adaptando-se a cada meia hora. | yfinance | M | Baixo |
| Resiliência a Notícias | Responde: Quais ativos estão ignorando más notícias hoje? Originalidade: Cruza menções em manchetes com desempenho tick-a-tick. | brapi | G | Alto |

## Ideias (Passo 7 - 2026-10-04 4)

| Índice de Fôlego (Divergência de Volume) | Responde: A alta do Ibovespa está perdendo força e prestes a reverter? Originalidade: Cruza retorno diário com queda de volume, focado em exaustão. | yfinance | P | Baixo |
| Sobrevivência Intraday (Sempre Verde) | Responde: Quem continuou no verde mesmo com o Ibov despencando intraday? Originalidade: Isolamento de força tick a tick. | yfinance | M | Baixo |
| Rotação de Capital (Bancos vs Commodities) | Responde: O dinheiro está saindo de commodities e indo para bancos hoje? Originalidade: Compara as duas maiores forças do Ibov (que ditam o rumo) para identificar se é dia de tendência ou rotação. | yfinance | P | Baixo |
| Experiência: Manchete Dinâmica | Responde: Consigo entender o clima do dia em uma frase sem ver gráficos? Originalidade: Template textual que traduz dados complexos em uma linha legível. | N/A | M | Baixo |
| Dispersão Extrema de Abertura | Responde: A abertura foi de pânico irracional ou o mercado está seletivo? Originalidade: Mede breadth de mercado isolando apenas os primeiros 30 min. | yfinance | M | Médio |

## Ideias (Passo 7 - 2026-10-05)

| Ideia | Detalhes | Fonte | Esforço | Risco |
|---|---|---|---|---|
| Compradores de Fundo (Reversão Intraday) | Responde: Quais ações abriram com forte queda e reverteram para alta? Originalidade: Identifica capitulação no intraday, mostrando força compradora oculta. | yfinance | M | Baixo |
| Mapa de Calor por Liquidez Absoluta | Responde: Onde está o dinheiro real do mercado hoje? Originalidade: Em vez de retorno %, mostra os maiores volumes financeiros transacionados no dia. | brapi / yfinance | M | Médio |
| Alerta de Vácuo de Livro | Responde: Quais ações estão perigosamente ilíquidas agora? Originalidade: Foca no risco de execução olhando para o spread bid/ask. | brapi | G | Alto |
| Ações Imunes ao Ibov | Responde: O que está subindo independentemente da queda forte do Ibov? Originalidade: Isola o beta e foca em ativos com correlação negativa pura no dia. | yfinance | P | Baixo |
| Histórico de Reação a Decisões do Copom | Responde: Como a bolsa reage em dias de decisão de juros? Originalidade: Cruza calendário econômico com retorno do pregão atual. | Scraping | G | Alto |
| Experiência: Modo "Foco no Risco" | Responde: Posso analisar o mercado sem o viés emocional das cores verde/vermelho? Originalidade: Redesign onde as cores dependem da volatilidade/volume, e não da direção do preço (verde/vermelho vira tons de cinza). | N/A | P | Baixo |

## Ideias (Passo 7 - 2026-10-05 2)

| Manchete Dinâmica (Clima do Dia) | Responde: Consigo entender o clima do dia em uma frase sem ver gráficos? Originalidade: Template textual que traduz dados complexos em uma linha legível. | N/A | M | Baixo |
| Navegação por Seções Tabulares | Responde: A página ficou longa demais? Originalidade: Troca o layout longo por abas ou seções, focando na navegação. | N/A | M | Baixo |
| Modo Contraste Extremo | Responde: Como garantir legibilidade em ambientes externos brilhantes? Originalidade: Foca puramente na acessibilidade visual do dashboard. | N/A | P | Baixo |
| Radar de Volume Intraday Quebrado | Responde: Quais ativos têm anomalia de volume apenas na última hora? Originalidade: Foco estrito no curto prazo, ignorando a média do dia todo. | yfinance | M | Baixo |
| Índice de Concentração Setorial | Responde: O capital está fluindo para um único setor hoje? Originalidade: Agregação por setor ao invés de ativo individual. | brapi | M | Baixo |

## Ideias (Passo 7 - 2026-10-06)

| Radar de Liquidez de Abertura | Responde: O capital grande já acordou hoje? Originalidade: Mede a velocidade de volume (R$/min) nos primeiros 15 min vs média histórica. | brapi | M | Baixo |
| Impacto da Curva de Juros | Responde: Quais ativos da bolsa estão reagindo ao DI futuro hoje? Originalidade: Cruza o retorno diário com as taxas de DI da B3 em tempo real. | B3/yfinance | G | Alto |
| Armadilha de Abertura (Gap Trap) | Responde: Quais ações abriram em forte alta (gap) mas já perderam tudo e estão no vermelho? Originalidade: Identifica armadilhas para compradores atrasados logo na primeira hora. | yfinance | M | Baixo |
| Exaustão por Volume Clímax | Responde: Essa queda livre acabou? Originalidade: Procura o maior pico de volume intraday em um dia de forte queda como sinal de capitulação. | brapi/yfinance | M | Médio |
| Experiência: Toggle Hoje vs Ontem | Responde: Como estava o mercado neste mesmo horário ontem? Originalidade: Permitir com um clique comparar o mapa atual com a foto exata de 24 horas atrás. | N/A | P | Baixo |
| Detecção de Movimento Silencioso | Responde: O que está subindo sem ninguém falar? Originalidade: Filtra ativos com retorno > 2% diário mas sem menções recentes no agregador de notícias. | brapi/Notícias | G | Alto |

## Ideias (Passo 7 - 2026-10-05 3)

| Índice de Sobrevivência Semanal (Sempre Verde) | Responde: Quais ativos fecharam todos os últimos 5 pregões no verde, independentemente do IBOV? Originalidade: Isola consistência extrema em vez de retorno total. | yfinance | P | Baixo |
| Anomalia de Leilão de Abertura (Spoofing Alert) | Responde: Quem está blefando no leilão antes de a bolsa abrir? Originalidade: Compara intenções vs abertura real. | B3/Brapi | G | Alto |
| Termômetro de Pânico vs Euforia Intraday | Responde: O mercado está em pânico vendedor ou em euforia compradora agora? Originalidade: Volume de bid vs ask. | Brapi/B3 | M | Médio |
| Top Perdedores do Mês | Responde: Quais ações mais caíram no mês atual? | yfinance | P | Baixo |
| Distorção de Fechamento (Falso Sinal) | Responde: A alta desta ação foi só por causa de um puxão no leilão de fechamento? Originalidade: Compara 16:50 com 17:00. | yfinance | M | Baixo |
| Experiência: Agrupamento Automático por Sentimento | Responde: Consigo ver apenas os alertas negativos juntos? Originalidade: Organiza a visão micro dinamicamente entre sinais de força e fraqueza. | N/A | M | Baixo |
| Experiência: Modo "Histórico de Crises" | Responde: Como estava este painel no dia do Joesley Day? Originalidade: Máquina do tempo global no dashboard. | N/A | G | Alto |

## Ideias (Passo 7 - 2026-10-05)

| Ideia | Detalhes | Fonte | Esforço | Risco |
|---|---|---|---|---|
| Termômetro de Liquidez Extrema | Responde: O mercado está travado ou eufórico? Originalidade: Usa o spread médio das 10 principais ações como proxy de estresse financeiro. | brapi | M | Médio |
| Detector de Pullback Falso | Responde: Essa queda no intraday é chance de compra ou reversão real? Originalidade: Cruza retorno negativo intraday com aumento de volume comprador oculto (VWAP). | yfinance | G | Alto |
| Alerta de Exaustão de Tendência Setorial | Responde: O rally deste setor acabou? Originalidade: Identifica quando 80% dos ativos de um setor fecham perto da mínima do dia após uma semana de alta. | yfinance | M | Baixo |
| Mapa de Consenso Dividido | Responde: Onde os analistas mais discordam hoje? Originalidade: Foca na dispersão do preço-alvo em vez da média, revelando incerteza extrema. | brapi | G | Alto |
| Impacto Cambial Cruzado | Responde: Como o DXY está esmagando ações domésticas hoje? Originalidade: Isola o efeito global (DXY) do efeito local (BRL=X) sobre as Small Caps. | yfinance | M | Médio |
| Experiência: Modo "Mapa de Calor Setorial Compacto" | Responde: Consigo ver todos os setores em um quadrado de 200px? Originalidade: Treemap ultra denso focado em cores e pesos, sem texto, para visão periférica. | N/A | P | Baixo |

## Ideias (fechamento da spec 025 - 2026-10-06)

| Ideia | Detalhes | Fonte | Esforço | Risco |
|---|---|---|---|---|

## Ideias (pedido do dono do produto - 2026-10-05)

| Ideia | Detalhes | Fonte | Esforço | Risco |
|---|---|---|---|---|
| Maré prevê alguma coisa? | Responde: depois de Pânico ou Otimismo extremo, o Ibovespa costuma andar para onde nos 5 pregões seguintes? Originalidade: backtest do próprio índice com amostra, janela e intervalo de confiança, antes de qualquer leitura preditiva aparecer no painel. | yfinance | G | Médio |
| Fluxo de ordens real na Maré | Responde: quem está agredindo o livro agora, comprador ou vendedor? Originalidade: troca o volume em alta da Maré por agressão por lado, se surgir fonte estável e gratuita. | a pesquisar | G | Alto |

## Ideias (Passo 7 - 2026-10-06 2)

| Ideia | Detalhes | Fonte | Esforço | Risco |
|---|---|---|---|---|
| Correlação Intraday com Dólar | Responde: Quem está sendo esmagado ou impulsionado pelo Dólar neste exato momento? Originalidade: Isola o beta contra o IBOV e correlaciona especificamente contra o BRL=X no intraday. | yfinance | M | Médio |
| Anomalia de Dia da Semana | Responde: As terças-feiras costumam ser vermelhas para o IBOV? Originalidade: Calcula a probabilidade baseada puramente na sazonalidade dos dias úteis. | yfinance | M | Baixo |
| Detector de Puxada de Leilão de Fechamento | Responde: Quem subiu ou desceu artificialmente no apagar das luzes? Originalidade: Mede o impacto exclusivo dos últimos 5 minutos no preço final e sinaliza distorções de preço provocadas apenas pelo fluxo de leilão. | brapi | G | Alto |
| Experiência: Abas de Navegação Contextual | Responde: É possível organizar as seções do dashboard de maneira que não fiquem escondidas por rolagem? Originalidade: Cria um menu lateral ou abas fixas focando na exploração por macrotemas (Cotações, Indicadores, Clima). | N/A | P | Baixo |

## Ideias (Passo 7 - 2026-10-07)

| Abas de Navegação Contextual | Responde: A página ficou longa demais e a informação está difícil de achar? Originalidade: Troca os filtros de exibição atuais por abas de navegação reais (Visão Geral, Risco, Rankings, Intraday), reorganizando estruturalmente o dashboard. | N/A | M | Baixo |
| Layout Híbrido Fixo/Rolagem | Responde: Como manter o contexto macro enquanto analiso detalhes micro? Originalidade: Fixa o Ibovespa e a Maré no topo da tela enquanto o resto rola. | N/A | P | Baixo |
| Índice de Sobrevenda Iminente | Responde: Qual ação em queda livre está prestes a repicar? Originalidade: Cruza quedas abruptas intraday (>3%) com picos isolados de volume (capitulação). | yfinance | M | Médio |
| Correlação com Curva de Juros (DI1) | Responde: Quem está sofrendo com a abertura da curva de juros hoje? Originalidade: Cruza dados de juros futuros da B3 com o retorno intraday das ações. | B3/yfinance | G | Alto |
| Alerta de Liquidez Seca | Responde: Onde o spread de compra/venda abriu perigosamente? Originalidade: Foca no risco de execução da ordem, não na variação de preço. | brapi | M | Médio |

## Ideias (Passo 7 - 2026-10-07 2)

| Ideia | Detalhes | Fonte | Esforço | Risco |
|---|---|---|---|---|
| Scanner de Capitulação por Clímax de Volume | Responde: Uma queda abrupta achou um piso momentâneo? Originalidade: Procura o maior pico isolado de volume intraday acompanhado de uma longa sombra inferior em dias de forte queda. | yfinance | G | Alto |
| Experiência: Comparação Ibovespa Dolarizado | Responde: Como a bolsa brasileira está performando para o investidor estrangeiro hoje? Originalidade: Toggle que divide instantaneamente o painel do IBOV pelo câmbio atual. | N/A | P | Baixo |
| Índice de Força Aberta | Responde: Quem continua subindo mesmo com o mercado devolvendo a alta da manhã? Originalidade: Mede especificamente a distância entre a máxima do dia e o preço atual, penalizando quem devolveu ganhos intraday. | brapi | M | Baixo |
| Termômetro de Liquidez Extrema (Spread Bid/Ask) | Responde: O mercado está travado ou perigosamente ilíquido? Originalidade: Usa a média de spread percentual das 10 principais ações como proxy de estresse no livro de ofertas. | brapi | M | Médio |

## Ideias (Passo 7 - 2026-10-08)

| Ideia | Detalhes | Fonte | Esforço | Risco |
|---|---|---|---|---|
| Experiência: Filtros de Tempo Dinâmicos | Responde: Consigo ver a mudança de sentimento da última hora vs o dia todo? Originalidade: Troca a visão de "hoje" por snapshots de diferentes momentos do pregão. | N/A | M | Baixo |
| Radar de Inflexão (Reversão de Tendência) | Responde: Qual ação reverteu uma longa tendência de baixa com força hoje? Originalidade: Foca na quebra de inércia, usando volume e preço cruzando médias curtas. | yfinance | M | Baixo |
| Alerta de Vácuo de Liquidez | Responde: Onde o spread no book de ofertas está assustadoramente alto agora? Originalidade: Olha a dificuldade de saída/entrada (risco de execução) e não a variação do preço. | brapi | M | Médio |
| Termômetro de Proteção Institucional (Skew de Opções) | Responde: Os grandes fundos estão pagando caro por proteção contra quedas agressivas? Originalidade: Usa derivativos para prever o medo que ainda não chegou no preço à vista. | B3 | G | Alto |
| Impacto Relativo do Exterior (BDRs vs IBOV) | Responde: O dia de hoje no Brasil é puramente reflexo lá de fora? Originalidade: Compara um índice de BDRs mais líquidos com as Blue Chips brasileiras em tempo real. | yfinance | M | Médio |

## Ideias (Revisão de Experiência - Passo 7 - 2026-10-09)

| Minimização de Painéis Indisponíveis | Responde: Consigo achar o que preciso, rápido? Evidência: A captura desktop mostra "Concentração Setorial" e "Concentração de Ganhos" ocupando muito espaço para exibir "Dado indisponível". Mudança: Ocultar painéis não essenciais ou exibi-los de forma compacta quando não há dados, para não ocupar o espaço de indicadores úteis. | N/A | P | Baixo |
| Destaque Visual para a Maré | Responde: Consigo achar o que preciso, rápido? Evidência: O gauge da Maré disputa atenção com os outros painéis. Mudança: Ajustar estilos para destacá-lo como termômetro primário. | N/A | P | Baixo |
| Reorganização dos Gauges de Tendência | Responde: Consigo achar o que preciso, rápido? Evidência: "Tendência (Ibovespa)" ocupa um painel próprio grande. Mudança: Movê-los para dentro do card principal do Ibovespa. | N/A | M | Baixo |

## Ideias (Passo 7 - 2026-10-10)

| Ideia | Detalhes | Fonte | Esforço | Risco |
|---|---|---|---|---|
| Tracker de Eventos Corporativos | Responde: Por que essa ação pulou 5% do nada? Originalidade: Exibe de forma rápida na visão micro se há dividendos, desdobramentos ou balanços da empresa no dia de hoje. | brapi | M | Médio |
| Dispersão do Volume (Onde está o dinheiro?) | Responde: O volume total está inflado por uma única ação? Originalidade: Exibe a proporção do volume financeiro total concentrado no top 3 ações do dia. | yfinance | M | Baixo |
| Radar de Inversão de Sentimento Intraday | Responde: O mercado abriu otimista, mas já reverteu? Originalidade: Conta quantas ações abriram em alta, mas já estão operando no vermelho, sinalizando armadilha bull trap coletiva. | yfinance | M | Médio |
| Histórico de "Maré" Extrema | Responde: Toda vez que a Maré atingiu este nível extremo de otimismo, o que aconteceu nos dias seguintes? Originalidade: Backtesting automático com os dados próprios cacheados do sistema. | Interna | G | Baixo |
| Experiência: Comparativo Visual Setorial | Responde: O setor bancário está puxando o Ibovespa sozinho? Originalidade: Um toggle no gráfico principal que exibe uma linha tracejada com um ETF setorial (como BOVA11 vs FIND11) para contexto imediato. | yfinance | M | Baixo |

## Ideias (Passo 7 - 2026-10-10 2)

| Ideia | Detalhes | Fonte | Esforço | Risco |
|---|---|---|---|---|
| Experiência: Agrupamento Inteligente de Alertas | Responde: Um mesmo ativo disparou múltiplos alertas hoje? Originalidade: Em vez de espalhar ativos por painéis de alerta, consolida os alertas (ex: Faca Caindo e Volume Anormal) por ticker na visão micro. | N/A | M | Baixo |
| Análise de Assimetria Risco/Retorno | Responde: Qual ativo está mais próximo do seu fundo dos últimos 30 dias do que do seu topo? Originalidade: Substitui análise de tendência pela pura distância percentual entre os extremos recentes. | yfinance | P | Baixo |
| Correlação Inversa Cripto (BTC vs B3) | Responde: O capital está saindo da bolsa para ativos de risco alternativos hoje? Originalidade: Compara a performance do IBOV e das principais ações brasileiras em relação ao movimento intradiário do Bitcoin (BTC-USD). | yfinance | M | Baixo |
| Alerta de Distorção da Primeira Hora | Responde: O ímpeto do leilão de abertura já morreu completamente? Originalidade: Identifica quando toda a variação direcional da primeira hora do pregão é completamente desfeita antes do almoço. | yfinance | M | Médio |

## Ideias (Passo 7 - 2026-10-11)

| Ideia | Detalhes | Fonte | Esforço | Risco |
|---|---|---|---|---|
| Radar de Congestionamento (Estreitamento de Bandas) | Responde: Qual ação está acumulando energia para um rompimento iminente? Originalidade: Foca na ausência extrema de volatilidade (compressão de preço) em vez de grandes movimentos diários. | yfinance | M | Baixo |
| Correlação Setorial Atípica | Responde: Qual ação está ignorando completamente o movimento de seus pares do mesmo setor hoje? Originalidade: Compara o ativo contra a média do seu próprio setor no intraday, destacando anomalias micro. | yfinance | M | Médio |
| Termômetro de Otimismo de Abertura (Taxa de Reversão) | Responde: A euforia da abertura do mercado tem se sustentado ou é sempre devolvida? Originalidade: Mede agregadamente nos últimos 30 dias a porcentagem de gaps de alta que fecharam no vermelho no IBOV. | yfinance | M | Baixo |
| Impacto de Fatores Externos (Commodities) | Responde: O peso das commodities está segurando o índice ou empurrando-o? Originalidade: Isola os tickers ligados a Minério e Petróleo para criar um sub-índice e contrastá-lo com o resto do IBOV. | yfinance | P | Baixo |
| Experiência: Modo "Terminal Bloomberg" | Responde: O layout tem muito espaço em branco para usuários hard-core? Originalidade: Um toggle no CSS que remove margens, reduz fontes e transforma os cards em grids densas e compactas. | N/A | P | Baixo |

## Ideias (Passo 7 - 2026-10-10 3)

| Ideia | Detalhes | Fonte | Esforço | Risco |
|---|---|---|---|---|
| Experiência: Densidade Condicional | Responde: Consigo ver mais contexto só quando preciso? Originalidade: Painéis colapsados que se expandem para revelar metadados adicionais apenas sob hover. | N/A | P | Baixo |
| Detector de Ação Órfã | Responde: Qual papel está largado às moscas? Originalidade: Busca ativos que não registraram nenhum negócio (spread vazio) nos últimos 15 minutos em horário de pico. | brapi | M | Médio |
| Termômetro de Concentração de Ordens | Responde: O volume é orgânico ou um único tubarão operando? Originalidade: Compara o número de negócios com o volume financeiro total para estimar o ticket médio intraday. | brapi | M | Médio |
| Radar de Inversão Pós-Notícia | Responde: O mercado "comprou no boato e vendeu no fato"? Originalidade: Destaca ativos que abriram forte com alto volume após anúncio, mas que agora operam perto da mínima do dia. | yfinance | M | Médio |
| Efeito Halo Setorial | Responde: Uma ação ruim está sendo puxada por um setor forte? Originalidade: Ativos com P/L muito ruim que estão subindo hoje puramente impulsionados por pares de setor. | brapi | M | Médio |

## Ideias (Passo 7 - 2026-10-12)

| Ideia | Detalhes | Fonte | Esforço | Risco |
|---|---|---|---|---|

| Índice de Esforço vs Resultado | Responde: Qual ação teve volume gigantesco hoje, mas o preço não andou? Originalidade: Cruza o aumento explosivo de volume (esforço) com um corpo de candle mínimo (resultado), sinalizando forte absorção de ordens. | yfinance | M | Baixo |
| Termômetro de Exaustão de Tendência | Responde: O rali de alta de um ativo já chegou ao limite? Originalidade: Procura o último suspiro de um movimento: volume climático acompanhado de pavio longo no topo, após múltiplos dias de alta. | yfinance | M | Médio |
| Painel de Incorrelação Agressiva | Responde: Que ação pesada no índice está desabando enquanto o mercado voa? Originalidade: Isola papéis do topo do IBOV operando na direção oposta ao benchmark com força (> 2% de diferença direcional). | brapi | M | Baixo |
| Radar do Leilão de Fechamento | Responde: Onde os institucionais estão montando posição nos minutos finais? Originalidade: Monitora variações extremas e picos de volume exclusivamentes nos últimos 15 minutos do pregão regular. | brapi | G | Alto |

## Ideias (Passo 7 - 2026-10-12 2)

| Ideia | Detalhes | Fonte | Esforço | Risco |
|---|---|---|---|---|
| Experiência: Heatmap Visual do Índice | Responde: Como está a distribuição do mercado de uma só vez? Originalidade: Troca a exibição tabular por uma grade de blocos proporcionais ao peso no Ibovespa, coloridos pela variação. | brapi / yfinance | M | Baixo |
| Índice de Rejeição de Fundo | Responde: Onde estão os compradores institucionais defendendo preço? Originalidade: Busca papéis que tocaram mínimas de 30 dias mas fecharam com sombra inferior igual ou maior que 50% do candle total. | yfinance | M | Médio |
| Termômetro de Correlacionamento do VIX | Responde: O mercado local está blindado do pânico externo hoje? Originalidade: Cruza variações extremas intraday do VIX americano (quando > +5%) com a resiliência momentânea do IBOV. | yfinance | P | Baixo |
| Alerta de Abertura Descolada | Responde: Quais ativos ignoraram o clima macro logo no leilão? Originalidade: Identifica ativos que abriram na direção oposta do gap do Ibovespa e com intensidade superior a 1%. | brapi | M | Baixo |


| Assimetria de Livro de Ofertas | Responde: Qual a pressão real do book em ativos de liquidez média? | brapi.dev | G | Alto (Limites de API) |
| Radar de Exaustão de Tendência | Responde: Quando um ativo subiu 5 dias seguidos com volume decrescente? | yfinance | M | Baixo |

## Ideias (Passo 7 - 2026-10-11)

| Experiência: Consolidação de Alertas em Menu Dinâmico | Responde: O excesso de alertas isolados polui a tela? Originalidade: Menu suspenso ou agrupado no mobile listando todas anomalias detectadas. | N/A | P | Baixo |
| Radar de Liquidez de Abertura | Responde: Onde o volume grande institucional acordou nos primeiros 30 min? Originalidade: Velocidade e picos de volume logo de manhã. | yfinance | M | Baixo |
| Sombra do Exterior na Abertura | Responde: Como o mercado abriu em relação ao SP500 futuro? Originalidade: Distingue variações locais vs arrasto gringo no leilão. | yfinance | M | Baixo |
| Assimetria de Livro de Ofertas e Pressão de Venda | Responde: Quem está sofrendo despejo forçado sem defesa? Originalidade: Leitura em tempo real de pressão. | brapi | G | Alto |
| Índice de Esforço vs Resultado | Responde: Muito volume e pouca alta? Absorção? Originalidade: VSA (Volume Spread Analysis) aplicada a ativos do IBOV no dia de hoje. | yfinance | M | Baixo |

## Ideias (Passo 7 - 2026-10-13)

| Ideia | Detalhes | Fonte | Esforço | Risco |
|---|---|---|---|---|
| Tracker de Dividendos Flash | Responde: Qual ação está pagando dividendo alto hoje? Originalidade: Cruza dados de proventos imediatos com a cotação intraday para ver se o mercado já precificou. | yfinance | M | Baixo |
| Radar de Squeeze de Volatilidade | Responde: Qual ativo está prestes a explodir (para cima ou para baixo)? Originalidade: Baseia-se no encurtamento extremo das bandas de Bollinger ou ATR nos últimos dias. | yfinance | M | Baixo |
| Sentimento de Notícias vs Preço | Responde: O mercado está ignorando notícias ruins? Originalidade: Compara a polaridade das manchetes recentes com a performance do ativo no dia. | brapi | G | Alto |
| Fator "Peso Pesado" | Responde: O IBOV está subindo só por causa da Vale ou Petrobras? Originalidade: Calcula a contribuição ponderada dos 5 maiores ativos para a pontuação diária do índice. | yfinance | M | Baixo |
| Alerta de Abertura em Extremos | Responde: O ativo abriu muito fora da curva? Originalidade: Detecta gaps de abertura que superam 2 desvios padrões do movimento médio diário. | yfinance | M | Baixo |
| Experiência: Reorganização por "Temperamento" | Responde: O que está calmo e o que está agitado? Originalidade: Agrupa os painéis secundários em abas de 'Alta Volatilidade' e 'Estabilidade' ao invés de categorização padrão. | N/A | P | Baixo |

## Ideias (Passo 7 - 2026-10-12)

| Ideia | Detalhes | Fonte | Esforço | Risco |
|---|---|---|---|---|
| Experiência: Reorganização de Alertas por Urgência | Responde: Quais alertas eu preciso olhar agora e quais podem esperar? Originalidade: Em vez de agrupar por tipo de alerta, consolida todos e ordena por intensidade do sinal, com um indicador visual de temperatura. | N/A | M | Baixo |
| Radar de Anomalia de Fechamento (Leilão) | Responde: Quais ações tiveram o preço distorcido no leilão de fechamento de ontem? Originalidade: Calcula a diferença entre o preço das 16:50 e o fechamento final para identificar movimentações bruscas (frequentemente revertidas na abertura). | yfinance | M | Baixo |
| Divergência IBOV vs Dólar na Última Hora | Responde: O mercado local está ignorando o dólar no curtíssimo prazo? Originalidade: Mede a correlação do Ibovespa e do Dólar na última hora para apontar anomalias de fluxo. | yfinance | M | Médio |
| Concentração de Força Vendedora | Responde: A queda de hoje é generalizada ou localizada em poucos ativos derretendo? Originalidade: Calcula quanto os 5 ativos com pior desempenho estão contribuindo negativamente para o índice, focando em isolar pânico. | yfinance | P | Baixo |
| Sensibilidade a Juros Futuros | Responde: Quais ativos estão sofrendo mais com a abertura da curva de juros hoje? Originalidade: Identifica os papéis mais inversamente correlacionados com o movimento de juros (DI) intradiário. | brapi | M | Médio |
| Radar de Rejeição de Topo (Sombra Superior) | Responde: Qual ativo tentou subir forte mas foi imediatamente amassado? Originalidade: Busca ações que registraram máxima intradiária >3% acima da abertura, mas que agora operam no negativo, indicando bull trap. | yfinance | M | Baixo |

| Experiência: Reorganização por Motores do Índice | Responde: O que realmente está movendo a bolsa hoje? Originalidade: Quebra o Ibovespa em "Motores" (Financeiro, Commodities, Doméstico) e reorganiza a página inicial priorizando qual deles está ditando o ritmo, em vez da grade estática tradicional. | yfinance / brapi | G | Médio (Complexidade em definir o peso de cada sub-índice) |
| Termômetro de Convicção (Fechamentos na Máxima) | Responde: O rali de hoje é frágil ou os institucionais estão segurando posição? Originalidade: Calcula a proporção de ações do Ibovespa fechando no terço superior de sua máxima diária, indicando forte intenção compradora. | yfinance | M | Baixo |
| Radar de Atividade de Leilão Anômala | Responde: Alguém sabe de algo que não sabemos? Originalidade: Compara o volume transacionado exclusivamente no leilão de abertura contra a média histórica dos leilões (não do intraday inteiro). | brapi | M | Alto (Falta de dados específicos de leilão em tempo real) |
| Sentimento Contrário Institucional | Responde: Onde os analistas estão errados (e o mercado está indo contra)? Originalidade: Cruza os 10 ativos com maior recomendação de "Venda" do consenso, mas que estão acumulando fortes altas nos últimos 15 dias. | Scraping CVM / yfinance | G | Alto (Problemas com scraping de recomendações) |
| Diferencial de Rendimento Ações vs Tesouro SELIC | Responde: O dividend yield médio da carteira B3 ainda compensa o risco da Selic de hoje? Originalidade: Não olha rentabilidade de cotação, mas o carrego. Proporcionaliza o DY acumulado dos últimos 12 meses das 20 maiores ações contra a taxa livre de risco atual diária. | yfinance / B3 | M | Baixo |

## Ideias (Passo 7 - 2026-10-13 2)

| Ideia | Detalhes | Fonte | Esforço | Risco |
|---|---|---|---|---|
| Experiência: Reorganização da Maré do Mercado | Responde: Consigo ler rapidamente a direção principal e seus motivadores? Originalidade: Condensação dos gauges da Maré e seus subindicadores em um formato mais denso para recuperar espaço vital na primeira dobra da página. | N/A | P | Baixo |
| Detector de Ação Órfã | Responde: Qual papel está largado às moscas? Originalidade: Busca ativos que não registraram nenhum negócio (spread vazio) nos últimos 15 minutos em horário de pico. | brapi | M | Médio |
| Termômetro de Concentração de Ordens | Responde: O volume é orgânico ou um único tubarão operando? Originalidade: Compara o número de negócios com o volume financeiro total para estimar o ticket médio intraday. | brapi | M | Médio |
| Radar de Inversão Pós-Notícia | Responde: O mercado "comprou no boato e vendeu no fato"? Originalidade: Destaca ativos que abriram forte com alto volume após anúncio, mas que agora operam perto da mínima do dia. | yfinance | M | Médio |
| Efeito Halo Setorial | Responde: Uma ação ruim está sendo puxada por um setor forte? Originalidade: Ativos com P/L muito ruim que estão subindo hoje puramente impulsionados por pares de setor. | brapi | M | Médio |
| Experiência: Agrupamento Dinâmico de Indicadores | Responde: Como ver apenas o que está fora do normal? Originalidade: Oculta painéis cujo valor está dentro de 1 desvio padrão da média, focando a atenção apenas em anomalias. | N/A | M | Baixo |
| Radar de Absorção em Topos | Responde: Qual ativo está sendo distribuído silenciosamente? Originalidade: Identifica aumento expressivo de volume no topo intradiário sem deslocamento correspondente no preço. | yfinance | M | Médio |
| Índice de Medo de Abertura | Responde: O mercado abriu em pânico ou calmo? Originalidade: Mede o tamanho médio dos gaps de abertura de toda a cesta no início do pregão. | yfinance | M | Baixo |
| Alerta de Ruptura Falsa Setorial | Responde: Um setor rompeu máxima mas falhou em seguida? Originalidade: Detecta falsos rompimentos agrupados por setor, e não apenas ações individuais. | brapi | M | Baixo |
## Ideias (Passo 7 - 2026-10-13-0929)

| Ideia | Detalhes | Fonte | Esforço | Risco |
|---|---|---|---|---|
| Termômetro de Clima Externo | Responde: O pânico ou euforia da abertura é local ou importado? Originalidade: Cruza S&P 500 Futuro e VIX americano para classificar o humor global antes das 10h. | yfinance | M | Baixo |
| Mapa de Dissonância Setorial | Responde: Quais ativos estão ignorando a maré do seu próprio setor? Originalidade: Destaca papéis que caem forte enquanto seu setor (ex. Bancos) sobe, evidenciando fatores idiossincráticos. | yfinance | M | Baixo |
| Termômetro de Sangria Institucional | Responde: O volume de venda está sendo feito às claras ou em blocos fracionados? Originalidade: Avalia a divergência entre a queda de preço e a contagem de ticks (negócios). | brapi | M | Alto (Falta API granular) |
| Filtro de Ações Imunes a Juros | Responde: Quais ações subiram consistentemente nos últimos dias de alta aguda do DI? Originalidade: Filtra diretamente o histórico cruzando a variação positiva do ativo apenas nos dias de estresse da curva de juros. | yfinance | M | Médio |
| Experiência: Modo TV / Kiosk | Responde: Posso deixar essa tela em um monitor secundário sem interação? Originalidade: Remove todos os controles interativos (abas, botões), esconde os detalhes miúdos e expande as fontes para leitura de longo alcance, focando na manchete, Ibovespa e alertas. | N/A | P | Baixo |

## Ideias (Passo 7 - 2026-10-15-0230)

| Ideia | Detalhes | Fonte | Esforço | Risco |
|---|---|---|---|---|
| Saúde Técnica: Instrumentação de Coleta Vazia | Responde: Quais painéis ficam vazios na maioria das vezes? Originalidade: Coleta telemetria do próprio sistema para basear a poda, não necessita de dados externos. | Banco SQLite | P | Baixo |
| Experiência: Abas por Intensidade | Responde: Como ordenar painéis pelo que mais destoa do normal? Originalidade: Oculta painéis normais e exibe os que romperam limites de desvio padrão. | N/A | M | Baixo |
| Radar de Reversão de Abertura | Responde: O que abriu caindo e já está subindo? Originalidade: Foca na primeira hora de negociação para buscar oportunidades de reversão intradiária. | yfinance | M | Baixo |
| Termômetro de Convicção Setorial | Responde: O setor todo sobe junto ou é só uma ação puxando? Originalidade: Mede a variância interna de retornos de cada setor listado. | yfinance | M | Médio |
| Painel de 'Sustos' (Gap + Sombra) | Responde: Quais ações tiveram gaps de baixa seguidos de forte rejeição nas primeiras horas? Originalidade: Indicador de suporte institucional ou forte defesa na mínima. | yfinance | M | Baixo |

## Ideias (Passo 7 - 2026-10-15-0429)

| Ideia | Detalhes | Fonte | Esforço | Risco |
|---|---|---|---|---|
| Radar de Anomalias de Spread | Responde: O market maker está em pânico? Originalidade: Detecta se o spread entre bid e ask de ações hiperlíquidas abriu subitamente, o que precede quedas bruscas antes mesmo do preço cair. | brapi | M | Alto |
| Termômetro de Concentração de Ordens | Responde: O volume é orgânico ou um único tubarão operando? Originalidade: Compara o número de negócios com o volume financeiro total para estimar o ticket médio intraday. | brapi | M | Médio |
| Experiência: Agrupamento Dinâmico de Indicadores | Responde: Como ver apenas o que está fora do normal? Originalidade: Oculta painéis cujo valor está dentro de 1 desvio padrão da média, focando a atenção apenas em anomalias. | N/A | M | Baixo |
| Saúde Técnica: Instrumentação de Coleta por Tempo | Responde: Quais painéis demoram mais para carregar? Originalidade: Registra o tempo de resposta da API por painel para basear futuras podas em custo computacional. | Banco SQLite | P | Baixo |
| Detector de Ação Órfã | Responde: Qual papel está largado às moscas? Originalidade: Busca ativos que não registraram nenhum negócio (spread vazio) nos últimos 15 minutos em horário de pico. | brapi | M | Médio |

## Ideias (Passo 7 - 2026-10-15-1154)

| Ideia | Detalhes | Fonte | Esforço | Risco |
|---|---|---|---|---|
| Radar de Anomalia de Preço no Leilão | Responde: O preço do fechamento foi manipulado? Originalidade: Identifica discrepâncias atípicas entre o último negócio antes do leilão e o preço de fechamento final. | yfinance / brapi | M | Baixo |
| Termômetro de Concentração de Ordens | Responde: O volume é orgânico ou um único tubarão operando? Originalidade: Compara o número de negócios com o volume financeiro total para estimar o ticket médio intraday. | brapi | M | Médio |
| Filtro de Divergência Ibov/Juros | Responde: Quais ativos estão ignorando a alta dos juros hoje? Originalidade: Busca papéis que sobem enquanto o DI (juros futuros) dispara, isolando força idiossincrática. | brapi | M | Médio |
| Saúde Técnica: Instrumentação de Tempo de Renderização | Responde: Quais painéis travam a página? Originalidade: Mede o tempo de geração do template no backend para subsidiar podas futuras. | Sistema | P | Baixo |
| Experiência: Modo TV / Kiosk | Responde: Posso deixar essa tela em um monitor secundário sem interação? Originalidade: Remove todos os controles interativos e expande as fontes para leitura de longo alcance. | N/A | P | Baixo |

## Ideias (Passo 7 - 2026-10-15-1527)

| Ideia | Detalhes | Fonte | Esforço | Risco |
|---|---|---|---|---|
| Termômetro de Exaustão de Tendência | Responde: O rali recente está perdendo fôlego? Originalidade: Busca ativos subindo por vários pregões consecutivos, mas com volume decrescente a cada dia. | yfinance | M | Baixo |
| Radar de Reversão de Abertura | Responde: O que abriu em pânico e já recuperou? Originalidade: Busca gaps de baixa > 1% na abertura que já viraram para alta no intraday, sinalizando suporte oculto. | yfinance | M | Baixo |
| Experiência: Agrupamento Dinâmico de Alertas | Responde: Como ver apenas o que está fora do normal? Originalidade: Esconde da interface alertas cujos desvios da média estão abaixo do normal, focando em anomalias extremas. | N/A | M | Baixo |
| Saúde Técnica: Otimização de Coleta Conjunta | Responde: A arquitetura atual aguenta mais coletores? Originalidade: Faz merge de requisições de diferentes coletores para as mesmas listas de ativos (ex: dados diários intraday), reduzindo chamadas ao yfinance. | N/A | M | Médio |
| Radar de Falsos Rompimentos Intraday | Responde: Qual ativo atraiu compradores no topo e voltou a cair? Originalidade: Busca ativos que romperam a máxima dos últimos 5 pregões na primeira hora, mas já recuaram para dentro do canal anterior. | yfinance | M | Baixo |

## Ideias (Passo 7 - 2026-10-16-0525)

| Ideia | Detalhes | Fonte | Esforço | Risco |
|---|---|---|---|---|
| Experiência: Modo Zen / Foco Técnico | Responde: Como reduzir o ruído visual no meio do pregão? Originalidade: Remove as cores intensas, minimiza tabelas e deixa o painel em tons de cinza focando apenas em desvios da média e manchetes principais. | N/A | P | Baixo |
| Saúde Técnica: Unificação de Histórico Diário | Responde: Os coletores estão repetindo requisições da mesma série histórica? Originalidade: Cria um cache compartilhado (e proxy local) onde um único pull do histórico diário do Ibov ou ativos alimenta múltiplos coletores. | Banco SQLite | M | Médio |
| Radar de Exaustão de Queda | Responde: Qual ativo caiu nos últimos pregões mas hoje apresenta rejeição com alto volume? Originalidade: Combina sequência de mínimas menores nos últimos 3 dias com uma abertura em gap de baixa que reverte positivamente intradiário. | yfinance | M | Baixo |
| Índice de Resiliência Intraday | Responde: Quem está segurando melhor as quedas do Ibovespa hoje? Originalidade: Compara o drawdown intradiário do ativo com o drawdown do Ibovespa, destacando ativos que não cederam às pressões do índice. | yfinance | M | Médio |
| Termômetro de Liquidez Oculta | Responde: O volume exibido no book é real ou há ordens iceberg? Originalidade: Avalia a proporção entre os negócios executados na pedra e as ofertas reais aparentes, estimando a presença de robôs ou institucionais operando fracionado. | brapi | M | Alto (Limitações da API) |

## Ideias (Passo 7 - 2026-10-16-1056)

| Ideia | Detalhes | Fonte | Esforço | Risco |
|---|---|---|---|---|
| Experiência: Reorganização do Topo | Responde: Como garantir que o Ibovespa fique no topo? Originalidade: Move os painéis 'Clima Global' e 'Motores do Índice' para baixo da primeira dobra, restaurando o protagonismo do Ibovespa e da Maré. | N/A | P | Baixo |
| Saúde Técnica: Proxy de Cotações Intraday | Responde: Como reduzir requisições redundantes? Originalidade: Concentra todos os pedidos de histórico de 1 dia num único cache/proxy para todos os coletores. | N/A | G | Alto |
| Capacidade Nova: Heatmap de Força Relativa | Responde: Qual setor está carregando o mercado? Originalidade: Agrupa os ativos por setor para exibir a força relativa setorial. | yfinance | M | Baixo |
| Poda: Remoção do Fator Peso Pesado | Responde: Vale a pena manter um painel frágil? Originalidade: Remove um painel que frequentemente apresenta falhas de coleta, limpando a UI. | N/A | P | Baixo |
| Capacidade Nova: Termômetro de Squeeze | Responde: Quais ativos estão sofrendo pressão institucional contra suporte? Originalidade: Detecta rompimento falso de suporte com volume elevado. | yfinance | M | Baixo |

## Ideias (Passo 7 - 2026-10-16-1326)

| Ideia | Detalhes | Fonte | Esforço | Risco |
|---|---|---|---|---|
| Radar de Resiliência de Baixa | Responde: Quem sobrevive ileso quando o Ibov afunda? Originalidade: Mostra apenas ações que subiram em todos os últimos 3 dias de queda forte (>1%) do Ibovespa. | yfinance | M | Médio |
| Termômetro de Ansiedade Intraday | Responde: Quão longe a máxima intradiária ficou da abertura em média na cesta B3? | yfinance | M | Baixo |
| Saúde Técnica: Instrumentação de Coleta por Tempo | Responde: Quais painéis demoram mais para carregar? Originalidade: Registra o tempo de resposta da API por painel para basear futuras podas em custo computacional. | Banco SQLite | P | Baixo |
