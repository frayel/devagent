---
id: 035
titulo: Reorganização dos Gauges de Tendência
status: ready
esforco: M
---

## Problema
Consigo achar o que preciso, rápido? Evidência: A seção "Tendência (Ibovespa)" ocupa um painel próprio grande (span-4), competindo com a Maré. Essa informação é intimamente ligada ao Ibovespa e poderia residir no próprio painel dele, simplificando a hierarquia visual.

## Comportamento esperado
- Mover os gauges de "MM21" e "MM200" para dentro do card principal do "Ibovespa hoje".
- Alterar o layout interno do painel do Ibovespa para acomodar as médias móveis (provavelmente ao lado ou abaixo do gráfico de preços) sem poluição visual.
- Remover o painel avulso "Tendência (Ibovespa)".

## Fontes de dados
N/A (Mudança puramente visual e de template). O dado já vem pelo cache do Ibovespa (`ibovespa_cache`).

## Cálculos
N/A

## Critérios de aceite
- [ ] O painel "Tendência (Ibovespa)" não existe mais na tela.
- [ ] O card "Ibovespa hoje" exibe as distâncias percentuais da MM21 e MM200 de forma integrada, usando macros do `docs/DESIGN.md`.
- [ ] `make telas` gera imagens em desktop e mobile mantendo a coerência do guia visual.

## Invariantes de produção
- N/A

## Fora do escopo
Alterar o método de cálculo das médias móveis.
