# ADR 009 · Postgres próprio no lugar do Neon

- **Data:** 2026-10-29 · **Status:** aceita
- **Revê:** ADRs 006 e 007 (provedor do Postgres)

## Contexto

Os ADRs 006 e 007 escolheram o Neon como Postgres de produção, pelo plano gratuito. Em 28/10 o Neon registrou mais de 4 GB de transferência de rede em poucos dias (spec 122), e o dono do produto trocou o banco por outro Postgres em 29/10.

## Decisão

1. O banco de produção é um Postgres externo apontado por `DATABASE_URL`, sem provedor fixado na documentação. O que vale é o contrato: Postgres com `psycopg`, snapshots por painel e pregão (ADR 007), SQLite só em testes e desenvolvimento local.
2. O item *Banco de dados* da `/sistema` passa a mostrar a versão do servidor (de `conn.info.server_version`, sem consulta a mais), o tamanho do banco (`pg_database_size`) e a latência, para que uma troca de provedor apareça na página.

## Consequências

- As restrições do plano gratuito do Neon (computação que desliga após 5 min parada, cota de horas e de transferência) deixam de valer. A redução de leitura da spec 122 continua útil, porque corta latência e custo em qualquer provedor.
- O texto dos ADRs 006 e 007 continua como registro histórico; o que mudou está aqui.
- Os limites do novo servidor (conexões, disco) ainda não estão medidos. A spec 129 (pool de conexões) deve conferi-los antes de fixar o tamanho do pool.
