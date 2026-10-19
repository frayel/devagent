---
id: 066
titulo: Radar de Anomalia de Fechamento
status: done
esforco: M
---

## Problema
Quais ações tiveram o preço distorcido no leilão de fechamento de ontem?

## Comportamento esperado
Adicionar um novo painel na interface que mostre as ações com movimentações bruscas e distorções calculadas no leilão de fechamento de ontem.

## Fontes de dados
yfinance

## Cálculos
Para os ativos de alta liquidez:
- Calcular a diferença entre o preço das 16:50 e o fechamento final.
- Identificar as ações que tiveram uma movimentação anormal, seja em preço e volume.

## Critérios de aceite
- [ ] O painel é exibido no frontend corretamente.
- [ ] O endpoint `/api/snapshot` inclui a chave `anomalia_fechamento`.
- [ ] Testes unitários para validar a lógica de seleção de anomalia.

## Invariantes de produção
- A chave `anomalia_fechamento` no JSON deve conter os ativos que realmente tiveram anomalia no fechamento.

## Fora do escopo
Criar gráficos detalhados do leilão (será apenas uma lista ou tabela).
