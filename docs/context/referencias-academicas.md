# Referências acadêmicas

Artigos sobre comportamento de preço, volume e microestrutura de mercado, em bolsas estrangeiras e na B3, reunidos pelo dono do projeto como ponto de partida para ideias. Consulte no Passo 7 (`devagent/skills/descobrir-ideias.md`) e antes de escrever uma spec que envolva sinal técnico, volume, pares ou livro de ofertas.

## Como usar

- Leia o artigo pelo link antes de citar um número dele numa spec. O resumo abaixo orienta a busca, não substitui a fonte.
- As seções gerais foram testadas em bolsas americanas e podem não se repetir na B3. Comece pela seção *Mercado brasileiro* quando houver um estudo equivalente e, nos demais casos, trate a ideia como hipótese e, quando der, meça com o histórico do próprio sistema antes de exibir como fato.
- Vários pedem dados que talvez não tenhamos (livro de ofertas, negócio a negócio). Confira `fontes-de-dados.md` antes de propor; se a fonte existir no MT5, a spec diz qual série usa.
- O usuário decide às 10h05 e não opera em alta frequência. Ideias de microestrutura servem como leitura do pregão (pressão, liquidez, risco), não como robô.
- Na spec, cite o artigo pela chave abaixo (ex.: `[Gatev 2006]`), e o painel mostra a referência ao lado do método, como pede a seção de transparência do `PRODUTO.md`.

## Regras técnicas e significância

**[Brock 1992]** Brock, Lakonishok & LeBaron. *Simple Technical Trading Rules and the Stochastic Properties of Stock Returns*. Journal of Finance, 1992. https://doi.org/10.1111/j.1540-6261.1992.tb04681.x
Testa médias móveis e rompimento de faixa em quase um século do Dow Jones e compara com séries simuladas por bootstrap sob modelos nulos (passeio aleatório, AR, GARCH). Sugere: avaliar um sinal técnico contra um modelo nulo antes de exibi-lo, e mostrar ao usuário se o sinal de hoje tem histórico melhor que o acaso.

**[Lo 2000]** Lo, Mamaysky & Wang. *Foundations of Technical Analysis: Computational Algorithms, Statistical Inference, and Empirical Implementation*. Journal of Finance, 2000. https://doi.org/10.1111/0022-1082.00265
Detecta padrões gráficos (ombro-cabeça-ombro, topos e fundos duplos, triângulos) de forma automática com regressão não paramétrica e testa se a distribuição dos retornos depois do padrão difere da incondicional. Sugere: reconhecer padrões sem regra subjetiva e informar o que costuma acontecer depois deles, com o tamanho da amostra.

## Volume como informação

**[Blume 1994]** Blume, Easley & O'Hara. *Market Statistics and Technical Analysis: The Role of Volume*. Journal of Finance, 1994. https://doi.org/10.1111/j.1540-6261.1994.tb04424.x
Modelo em que o volume carrega informação sobre a qualidade e a dispersão do que os participantes sabem, informação que o preço sozinho não revela. Sugere: tratar o volume como medida de confiança de um movimento, não só como coluna da tabela.

**[Llorente 2002]** Llorente, Michaely, Saar & Wang. *Dynamic Volume-Return Relation of Individual Stocks*. Review of Financial Studies, 2002. https://doi.org/10.1093/rfs/15.4.1005
Separa negociação por informação de negociação por proteção (hedge): no primeiro caso, retorno com volume alto tende a continuar; no segundo, a reverter. O efeito varia com o grau de assimetria de informação da ação (tamanho, spread, cobertura). Sugere: classificar cada ação pela tendência de continuar ou reverter depois de dias de volume alto, medida no próprio histórico.

## Valor relativo

**[Gatev 2006]** Gatev, Goetzmann & Rouwenhorst. *Pairs Trading: Performance of a Relative-Value Arbitrage Rule*. Review of Financial Studies, 2006. https://doi.org/10.1093/rfs/hhj020
Forma pares de ações cujos preços normalizados andaram juntos num período de formação e acompanha quando o par se afasta além de um limiar. Sugere: um painel de pares do Ibovespa que se descolaram do comportamento habitual, com quanto tempo pares assim costumam levar para voltar e com que frequência não voltam.

**[Avellaneda 2010]** Avellaneda & Lee. *Statistical Arbitrage in the U.S. Equities Market*. Quantitative Finance, 2010. https://doi.org/10.1080/14697680903124632
Explica o retorno de cada ação por fatores (componentes principais ou ETFs setoriais) e modela o resíduo como processo que volta à média, gerando um escore de afastamento. Mostra também que o desempenho mudou com o tempo. Sugere: escore de "fora do lugar em relação ao setor" para cada ação, separando o movimento do mercado do movimento próprio.

## Microestrutura e livro de ofertas

**[Cont 2014]** Cont, Kukanov & Stoikov. *The Price Impact of Order Book Events*. Journal of Financial Econometrics, 2014. https://doi.org/10.1093/jjfinec/nbt003
Mostra que o desequilíbrio do fluxo de ordens no melhor nível do livro (order flow imbalance) explica boa parte da variação de preço de curto prazo, com impacto inversamente proporcional à profundidade. Sugere: indicador de pressão compradora ou vendedora intradiária, se o MT5 entregar o livro.

**[Easley 2012]** Easley, López de Prado & O'Hara. *Flow Toxicity and Liquidity in a High-Frequency World*. Review of Financial Studies, 2012. https://doi.org/10.1093/rfs/hhs053
Propõe o VPIN, medida de toxicidade do fluxo calculada em "tempo de volume" (baldes de volume igual) em vez de tempo de relógio, associada a episódios de falta de liquidez. Sugere: alerta de fluxo desequilibrado num ativo ou no índice, com o aviso de que a medida é debatida na literatura.

**[Sirignano 2019]** Sirignano & Cont. *Universal Features of Price Formation in Financial Markets: Perspectives from Deep Learning*. Quantitative Finance, 2019. https://doi.org/10.1080/14697688.2019.1622295
Redes neurais treinadas com dados de livro de ofertas de muitas ações juntas preveem a direção do próximo movimento melhor que modelos treinados ação por ação, indicando padrões comuns na formação de preço. Sugere: ao modelar qualquer previsão, treinar com o conjunto do Ibovespa em vez de um modelo por ativo. Exige dados e infraestrutura que hoje não temos: registre o custo antes de propor.

## Mercado brasileiro

Estudos feitos com dados da B3 (e das antigas Bovespa e BM&F). Valem mais que os americanos como ponto de partida, porque já mostram onde o Brasil se comporta diferente. Vários são de periódicos nacionais sem DOI; o link aponta para a página oficial do artigo.

### Tendência, reversão e regras técnicas

**[Bonomo 2003]** Bonomo & Dall'Agnol. *Retornos anormais e estratégias contrárias*. Revista Brasileira de Finanças, v. 1, n. 2, 2003. https://ideas.repec.org/a/brf/journl/v1y2003i2p165-215.html
Com dados de 1986 a 2000, comprar perdedores e vender vencedores deu retorno anormal em horizontes de 3 meses a 3 anos, e não houve efeito momento como nos EUA. O ganho caiu depois do Plano Real.

**[Piccoli 2015]** Piccoli, Souza, Silva & Cruz. *Revisitando as estratégias de momento: o mercado brasileiro é realmente uma exceção?* RAUSP, v. 50, n. 2, 2015. https://doi.org/10.5700/rausp1193
De 1997 a 2014, a carteira de momento teve retorno positivo e significativo fora das crises, mas desabou nelas, o que apaga boa parte do lucro na média. Lido junto com [Bonomo 2003], sugere: um painel que mostra se o mercado está num regime que favorece seguir a tendência ou apostar na reversão.

**[Baptista 2008]** Baptista & Valls Pereira. *Analysis of performance of technical trading rules applied to the market of intraday Ibovespa index futures contracts*. Revista Brasileira de Finanças, v. 6, n. 2, 2008. https://ideas.repec.org/a/brf/journl/v6y2008i2p205-234.html
Regras técnicas aplicadas negócio a negócio ao futuro de Ibovespa, agrupadas por desempenho e validadas em períodos seguintes. Superaram o comprar e manter, mas custos e atraso de execução realistas reduzem o ganho.

**[Miralles-Quirós 2018]** Miralles-Quirós, Miralles-Quirós & Gonçalves. *Profitability of Technical Trading Rules in the Brazilian stock market*. Revista Evidenciação Contábil & Finanças, v. 6, n. 2, 2018. https://doi.org/10.18405/RECFIN20180208
Compara regras clássicas com uma regra de taxa de variação (Rate of Change) em ETFs de empresas grandes, médias e pequenas, com testes contra mineração de dados (Reality Check, SPA). A regra de momento foi melhor que as clássicas, e o ETF de pequenas rendeu mais. Sugere: aplicar os mesmos testes contra mineração de dados a qualquer sinal que o painel exiba.

### Volume

**[Medeiros 2008]** Medeiros & Van Doornik. *The Empirical Relationship Between Stock Returns, Return Volatility and Trading Volume in the Brazilian Stock Market*. Brazilian Business Review, v. 5, n. 1, 2008. https://bbronline.com.br/index.php/bbr/article/view/447
Com o Ibovespa de 2000 a 2005, retorno e volume se relacionam, mas um ajuda pouco a prever o outro. Já volume e volatilidade se antecipam mutuamente (causalidade de Granger). Sugere: usar o volume para prever agitação, não direção.

**[Iquiapaza 2010]** Iquiapaza, Bressan & Amaral. *Previsão não-linear de retornos na BOVESPA: volume negociado em um modelo auto-regressivo de transição suave*. RAC, v. 14, n. 1, 2010. https://rac.anpad.org.br/index.php/rac/article/view/729
Modelo de transição suave (LSTAR) com o volume como variável de troca de regime, de 1996 a 2006. Com custo de 0,5% por operação não gera ganho extra; com custo baixo, o retorno ajustado ao risco melhora. Bom lembrete de que o custo decide se um sinal serve.

### Pares e valor relativo

**[Perlin 2007]** Perlin. *Evaluation of pairs trading strategy at the Brazilian financial market*. MPRA Paper 8308, 2007. https://ideas.repec.org/p/pra/mprapa/8308.html (versão publicada no Journal of Derivatives & Hedge Funds: https://doi.org/10.1057/jdhf.2009.4)
Pares no mercado brasileiro foram lucrativos e neutros ao mercado em várias combinações de parâmetros, e os dados diários deram resultado melhor que os semanais e mensais.

**[Caldeira 2013]** Caldeira & Moura. *Selection of a Portfolio of Pairs Based on Cointegration: A Statistical Arbitrage Strategy*. Revista Brasileira de Finanças, v. 11, n. 1, 2013. https://doaj.org/article/b51aacdd28a8469ca0cc582e7ac1ef47
Escolhe pares por cointegração, modela o spread como processo que volta à média e testa de 2005 a 2012: retorno excedente de 16,38% ao ano, Sharpe de 1,34 e pouca correlação com o mercado. É a versão brasileira de [Gatev 2006] e o melhor ponto de partida para um painel de pares.

### Fluxo estrangeiro e fatores

**[Loncan 2015]** Loncan & Caldeira. *Foreign portfolio capital flows and stock returns: a study of Brazilian listed firms*. Estudos Econômicos, v. 45, n. 4, 2015. https://doi.org/10.1590/0101-416145456tlj
Entrada de capital estrangeiro eleva o Ibovespa, com efeito maior em commodities, indústria e consumo cíclico, em ações de beta alto e no Novo Mercado; ações de beta baixo perdem. Sugere: mostrar, quando o estrangeiro entra ou sai, quais setores e ações costumam reagir mais, cruzamento já previsto na seção 8 do `PRODUTO.md`.

**[Lewin 2025]** Lewin & Campani. *Optimal constrained strategies for factor-based investing in the Brazilian stock market*. Revista Contabilidade & Finanças, 2025. https://doi.org/10.1590/1808-057x20242051.en
Identifica quatro fatores de risco no Brasil e mostra que estratégias que trocam de exposição conforme o regime de mercado tiveram Sharpe melhor que as de regime único. Reforça a ideia de detectar regime antes de recomendar.

### Microestrutura e comportamento do investidor

**[Alexandre 2018]** Alexandre, Ferreira & Rodrigues Neto. *Order book, order flow and returns: evidence from the Brazilian stock exchange*. Redeca, v. 5, n. 1, 2018. https://doi.org/10.23925/2446-9513.2018v5i1p24-38
Estuda o livro de ofertas das vinte ações mais negociadas da Bovespa de 2006 a 2009: parte dos fatos estilizados de outros países se confirma aqui, parte não. Leia antes de aplicar [Cont 2014] ou [Easley 2012] na B3.

**[Chague 2020]** Chague, De-Losso & Giovannetti. *Day trading for a living?* Texto para discussão 525, FGV EESP, 2020. https://econpapers.repec.org/RePEc:fgv:eesptd:525
Entre os que começaram a operar day trade no mercado futuro brasileiro de 2013 a 2015 e persistiram por 300 dias ou mais, 97% perderam dinheiro e só 0,4% ganharam mais que um bancário. Serve de limite para o consultor: o produto informa a decisão do usuário, não o empurra para girar a carteira.
