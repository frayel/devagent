---
id: 033
titulo: Radar de Anomalia de Peso Relativo Intraday
status: ready
esforco: M
---

## Problema
O usuário quer saber quais pesos-pesados estão distorcendo o Ibovespa contra o resto do mercado hoje, isolando os poucos ativos que movem o índice sozinhos.

## Comportamento esperado
Adicionar um novo painel "Anomalia de Peso" na seção "Rankings & Destaques".
O painel exibe uma tabela com as 3 ações que mais estão impactando (positiva ou negativamente) o Ibovespa no dia, mostrando o ticker e o impacto estimado em pontos de índice.
O painel degrada amigavelmente exibindo "Dados indisponíveis" caso a fonte falhe.

## Fontes de dados
`yfinance` (endpoint spark ou regular para cotação e volume dos principais componentes do IBOV).
A composição teórica e os pesos do IBOV podem ser aproximados ou puxados de brapi/yfinance, mas para este MVP, assumiremos pesos fixos ou simplificados baseados nos top 5 ativos (VALE3, PETR4, ITUB4, BBDC4, B3SA3) que concentram peso relevante.
Plano B: fallback seguro ignorando ativos que derem timeout, degradando a soma do impacto ou ocultando o painel caso os dados centrais falhem.

## Cálculos
Para os pesos-pesados selecionados (ex: VALE3, PETR4, ITUB4, BBDC4, B3SA3, ELET3), calcular o impacto em pontos na variação diária aproximada:
Impacto = Variação % do ativo * Peso aproximado * Pontuação do Ibovespa Anterior / 100
Filtrar os 3 ativos de maior impacto absoluto e ordená-los.

## Critérios de aceite
- [ ] O backend tem teste unitário para o serviço e cálculo do impacto, usando retornos simulados.
- [ ] A chave `anomalia_peso` no snapshot `/api/snapshot` retorna uma lista válida de ações em formato JSON.
- [ ] A interface exibe a tabela de anomalia de peso e degrada corretamente quando o retorno da API falha.

## Invariantes de produção
A chave `anomalia_peso` em `/api/snapshot` retorna uma lista de dicionários com formato válido (ticker, impacto).

## Fora do escopo
Não calcularemos os pesos diários exatos da carteira B3 inteira. Não faremos gráficos para este painel no momento.
