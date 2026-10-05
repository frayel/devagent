---
id: 024
titulo: Índice de Sobrevivência Semanal (Sempre Verde)
status: done
esforco: P
---

## Problema
Em semanas voláteis, o investidor quer saber quais ações são porto seguro e mostram força compradora constante. Ele pergunta: "Quais papéis fecharam no verde todos os dias na última semana, ignorando as quedas do Ibovespa?"

## Comportamento esperado
Adicionar um painel na visão micro chamado "Sempre Verde" ou "Sobrevivência Semanal". O painel exibirá uma lista de papéis (no máximo 5) que tiveram fechamento positivo em cada um dos últimos 5 pregões.
Para cada ativo, exibir o ticker e a sequência de "dias de alta seguidos" (que será igual ou maior que 5).
Caso nenhum ativo cumpra a regra, exibir "Nenhum ativo sobreviveu invicto nos últimos 5 dias."

## Fontes de dados
yfinance. Coleta diária (após fechamento) do histórico de 7 dias (`period=7d` ou `1mo` e filtro os 5 últimos pregões). Se a fonte falhar, o painel exibe "Dados não disponíveis".

## Cálculos
1. Para a lista de 30 ações de alta liquidez já acompanhadas.
2. Extrair os últimos 5 dias com dados de fechamento.
3. Para cada dia, calcular se o fechamento atual é maior que o fechamento anterior.
4. Retornar os tickers onde todos os 5 dias testados foram positivos.

## Critérios de aceite
- [ ] Função de filtro em service identifica corretamente papéis com 5 dias consecutivos de alta num mock de dados.
- [ ] O componente não quebra a página caso a lista de papéis aprovados seja vazia, exibindo estado vazio correspondente.
- [ ] Exposição dos ativos identificados no payload JSON do `/api/snapshot`.

## Invariantes de produção
- O painel exibe apenas papéis que efetivamente tiveram retornos diários positivos nos últimos 5 dias.
- A ausência de ativos não causa erro na aplicação.

## Fora do escopo
- Calcular "sobrevivência" para prazos maiores (mensal/anual).
- Gráficos detalhados da curva de preços do ativo.
