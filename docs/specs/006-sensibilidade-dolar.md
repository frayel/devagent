---
id: 006
titulo: Sensibilidade ao Dólar
status: ready
esforco: P
---

## Problema
Em dias de forte movimento cambial, o investidor não sabe quais papéis da sua carteira se beneficiam naturalmente da alta ou baixa do dólar. Esta feature identifica a correlação recente.

## Comportamento esperado
- Uma tabela com as 3 ações (dentre as 30 mais líquidas) com maior correlação positiva ao dólar e as 3 com maior correlação negativa nos últimos 30 dias.
- Adição da seção ao payload do `/api/snapshot`.

## Fontes de dados
- yfinance (`BRL=X` para o dólar, ações via `spark` ou loop `chart`).
- brapi.dev para ações (se fallback).
- Frequência: agendador do web service. Cache local SQLite em `dolar_correlation_cache`.
- Plano B: degradação graciosa com mensagem "Dados não disponíveis".

## Cálculos
- Coletar as variações percentuais diárias das últimas 30 barras para as ações e para `BRL=X`.
- Calcular a correlação de Pearson entre as séries.

## Critérios de aceite
- [ ] O componente aparece na UI se os dados estiverem disponíveis.
- [ ] Resposta simulada por testes exibe a tabela de correlações com nomes e valores calculados.
- [ ] Fallback lida corretamente com ausência de dados do dólar e exibe log de erro apropriado e UI limpa sem quebrar a tela.

## Invariantes de produção
- A lista de ações deve ter entre 0 e 3 itens por seção.
- O campo `coletado_em` tem que estar presente no snapshot.

## Fora do escopo
- Explicação microeconômica do motivo da correlação (ex: receitas de exportação).
- Cálculo histórico superior a 30 dias de pregão.
