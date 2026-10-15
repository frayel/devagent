---
id: 056
titulo: Saúde Técnica: Instrumentação de Coleta Vazia
status: done
esforco: P
gaveta: saúde técnica
---

## Problema
O sistema carece de uma telemetria para medir quanto tempo ou quantas coletas cada painel passa sem dados, dificultando as decisões de poda com embasamento estatístico.

## Comportamento esperado
O sistema não terá alterações visíveis imediatas para o usuário, mas internamente criará um registro base no banco de dados, em memória ou arquivo de log, toda vez que um ciclo de coleta resultar em um estado "sem dados" ou vazio para qualquer painel.

## Fontes de dados
Nenhuma nova fonte externa de dados; utiliza o próprio estado de coleta interno do SQLite ou log do scheduler.

## Cálculos
Para o MVP, a coleta deve simplesmente incrementar um contador no banco (ou log) para as chaves em que não houve dados gerados, para ser usado em futuras decisões de poda (ex.: contar falhas ou "não-atualizações").

## Critérios de aceite
- [ ] O comportamento visível da página principal e da API (/api/snapshot) não muda e os testes existentes continuam passando.
- [ ] Existe uma rotina ou tabela básica que viabilize registrar as falhas/coletas vazias, com pelo menos uma contagem incrementada para testes.
- [ ] O banco de dados ou estrutura subjacente é ajustado sem quebrar chamadas anteriores.

## Invariantes de produção
- A página continua exibindo a mesma quantidade e estado dos painéis anteriores.

## Fora do escopo
Implementação de regras automáticas de poda nesta spec (apenas a instrumentação inicial).
