---
id: 058
titulo: Termômetro de Concentração de Ordens
status: ready
esforco: M
---

## Problema
O volume financeiro total de um ativo não diz se a movimentação foi causada por muitos pequenos investidores ou por poucos grandes fundos (tubarões). O investidor quer saber se um movimento expressivo está concentrado em poucas e grandes ordens, o que indica atuação institucional mais forte.

## Comportamento esperado
Na seção "Visão Micro" (ou equivalente), um painel `span-4` (ou integrado a tabelas existentes) exibirá as 3 a 5 ações de alta liquidez que apresentam a maior relação entre volume financeiro e número de negócios (Ticket Médio Intraday) no dia de hoje, comparado ao seu ticket médio padrão. O painel deve destacar a "Concentração de Lotes" de forma visual.

## Fontes de dados
A API do brapi.dev fornece volume e, em alguns endpoints/planos, número de negócios diário. Como plano B ou fallback de dados, se o número de negócios não estiver disponível via API pública sem custo abusivo, usaremos os dados da B3 fornecidos no final do dia, mas focado no intraday, a fonte primária deve ser investigada. Se nenhuma fonte retornar a contagem de `trades` ou `ticks`, o painel exibirá "Dados indisponíveis".

## Cálculos
`Ticket Médio = Volume Financeiro Total / Número de Negócios`
`Concentração = Ticket Médio Atual / Ticket Médio Histórico (ou do dia anterior)`
Exibe os ativos com maior índice de `Concentração`.

## Critérios de aceite
- [ ] O sistema coleta dados de volume e número de negócios (caso disponível na API do brapi.dev ou yfinance).
- [ ] O painel é renderizado sem quebrar o layout se houver dados.
- [ ] Fallback tratado adequadamente ("Dados indisponíveis") caso a métrica de número de trades não exista na fonte.
- [ ] Teste automatizado com fixture simulando a resposta da API com trades e volumes.

## Invariantes de produção
- A chave `concentracao_ordens` (ou equivalente) é exportada no `/api/snapshot`.
- O cálculo deve evitar divisão por zero (se número de negócios for zero, a métrica é nula).

## Fora do escopo
Cálculo de VWAP real por ordem ou extração do livro de ofertas em tempo real. O indicador se baseia apenas no agregado de volume financeiro e quantidade de trades do dia.
