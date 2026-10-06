# Backlog

## Correções (prioridade sobre qualquer feature)

- **Valores únicos sem escala.** Implementar a spec `docs/specs/026-gauges-valores-unicos.md` seguindo as seções 5.1 e 5.2 do `docs/DESIGN.md` (pedido do dono do produto em 05/10/2026). Ao concluir, marque a spec como `done`, remova esta entrada e registre no `CHANGELOG.md`.
- **Maré do mercado.** Implementar a spec `docs/specs/027-indice-mare.md` depois da 026, porque usa a macro `gauge` (pedido do dono do produto em 05/10/2026). Ao concluir, marque a spec como `done`, remova esta entrada e registre no `CHANGELOG.md`.

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
| Agrupamento de Força Setorial | Mede a dispersão dentro de um mesmo setor para achar anomalias | brapi | M | Baixo |
| Variação vs IBOV (Força Relativa Diária) | Exibir o alfa diário gerado em relação ao benchmark | yfinance | P | Baixo |
| Ações "Esquecidas" (Volume sumiu) | Oportunidades em ativos que secaram de liquidez recentemente | yfinance | P | Baixo |

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
| Anomalia de Peso Relativo | Responde: Quais pesos-pesados estão segurando o Ibov sozinhos? Originalidade: Mede o impacto individual em pontos de índice, em vez do retorno %. | brapi/yfinance | M | Médio |
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
| Setor líder por volume financeiro | Responde: para qual setor o dinheiro está indo hoje, em reais, e não em %? Completa a Concentração Setorial (spec 025), que mostra só o líder por variação média. | brapi / yfinance | P | Baixo |

## Ideias (pedido do dono do produto - 2026-10-05)

| Ideia | Detalhes | Fonte | Esforço | Risco |
|---|---|---|---|---|
| Sparklines nos rankings | Responde: a alta de hoje é ponto fora da curva ou continuação? Originalidade: cada linha de Maiores altas, Maiores baixas e Força Relativa ganha um minigráfico de 10 pregões ao lado da variação (DESIGN.md, seção 5.1). | yfinance | M | Baixo |
| Maré prevê alguma coisa? | Responde: depois de Pânico ou Otimismo extremo, o Ibovespa costuma andar para onde nos 5 pregões seguintes? Originalidade: backtest do próprio índice com amostra, janela e intervalo de confiança, antes de qualquer leitura preditiva aparecer no painel. | yfinance | G | Médio |
| Fluxo de ordens real na Maré | Responde: quem está agredindo o livro agora, comprador ou vendedor? Originalidade: troca o volume em alta da Maré por agressão por lado, se surgir fonte estável e gratuita. | a pesquisar | G | Alto |
