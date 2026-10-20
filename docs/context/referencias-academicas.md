# Referências acadêmicas

Artigos sobre comportamento de preço, volume e microestrutura de mercado, indicados pelo dono do projeto como ponto de partida para ideias. Consulte no Passo 7 (`devagent/skills/descobrir-ideias.md`) e antes de escrever uma spec que envolva sinal técnico, volume, pares ou livro de ofertas.

## Como usar

- Leia o artigo pelo DOI antes de citar um número dele numa spec. O resumo abaixo orienta a busca, não substitui a fonte.
- Quase todos foram testados em bolsas americanas. Na B3 o resultado pode não se repetir: trate a ideia como hipótese e, quando der, meça com o histórico do próprio sistema antes de exibir como fato.
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
