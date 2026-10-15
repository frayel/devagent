---
id: 057
titulo: Radar de Anomalias de Spread (Medo do Market Maker)
status: ready
esforco: M
---

## Problema
Em momentos de pânico incipiente, o preço pode ainda não ter caído, mas os formadores de mercado retiram suas ordens de compra, aumentando subitamente o spread entre a melhor oferta de compra e a melhor de venda de ativos altamente líquidos. Isso não é coberto por indicadores baseados apenas no último negócio. O usuário quer saber onde o pânico invisível está começando.

## Comportamento esperado
Na seção "Alertas Intraday", um novo painel lista até 5 ações de alta liquidez cujo spread percentual atual (ask - bid / bid) é anormalmente superior à sua média histórica (ex: >3x a média dos últimos 5 pregões no mesmo horário). A exibição mostra o ticker e a porcentagem atual de spread. Se não houver anomalias, exibe "Spreads normais hoje".

## Fontes de dados
A API do MT5 ou brapi.dev (usando `get_quote` com detalhes de bid/ask). Prioridade para brapi.dev caso MT5 falhe.
Limites: requisições dentro do teto normal; dados coletados em batch.
Plano B: se as fontes não retornarem bid/ask no intraday, o painel exibe "Dados indisponíveis".

## Cálculos
Para uma cesta das 10 ações mais líquidas do IBOV:
`Spread % = (Ask - Bid) / Bid * 100`
O estado normal para essas ações é um spread menor que 0.1%. Consideramos anomalia um spread atual acima de 0.5% com volume diário em andamento maior que 0. A comparação ideal seria com o spread histórico, mas para MVP, threshold fixo de 0.5% para ativos hiperlíquidos (que usualmente têm 1-2 centavos de spread) já captura a anomalia.

## Critérios de aceite
- [ ] O painel é exibido em "Alertas Intraday" se o layout e agrupamentos permitirem, com a lista dos tickers e seus spreads afetados.
- [ ] Teste automatizado com fixture simulando uma resposta com ask e bid distantes deve mostrar o ticker no painel.
- [ ] Caso ask ou bid seja 0, ignora para evitar divisão por zero ou falsos positivos em leilões.

## Invariantes de produção
- A chave `anomalias_spread` deve estar presente no endpoint `/api/snapshot`.
- Só mostra dados durante o pregão ativo ou logo após o fechamento, considerando os dados mais recentes.

## Fora do escopo
Cálculo de média de spread histórica real armazenada no banco. O MVP usa um limite fixo para as ações da cesta de hiperliquidez.
