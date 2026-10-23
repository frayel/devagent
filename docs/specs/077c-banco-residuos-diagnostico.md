---
id: 077c
titulo: Resíduos do SQLite depois da migração (Diagnóstico do banco)
status: ready
esforco: P
gaveta: saúde técnica
aceite: tests/test_aceite_077c.py
---

## Problema

Página /sistema mede o banco errado. `app/database.py::diagnostico()` (spec 082) crava `"tipo": "SQLite"`, conta tabelas e mede o tamanho do `data.db`, sem perguntar a `app/banco.py` qual backend está ativo. Com `DATABASE_URL` configurado, `verificar_banco()` mostra em Atenção "a aplicação ainda grava no SQLite local...". É falso positivo, e o ciclo de saúde de produção (ADR 016) lê essa página para decidir o que corrigir.

## Comportamento esperado

### Diagnóstico do banco
- `diagnostico()` muda para `app/banco.py` e descreve o backend de `get_backend_type()`:
  - Postgres: `tipo = "Postgres"`, tabelas por `SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'`, tamanho por `pg_database_size(current_database())`, latência medida na mesma conexão.
  - SQLite: o comportamento atual.
- `database_url` continua indicando se a variável existe, nunca o valor.
- `verificar_banco()` em `app/services/sistema.py`:
  - Postgres conectado: OK.
  - SQLite com `DATABASE_URL` configurado só acontece quando o Postgres não respondeu na partida (`_determine_backend` caiu para `sqlite_efemero`). Continua Atenção, com o texto: "DATABASE_URL está configurado, mas o Postgres não respondeu quando a instância subiu; a aplicação está gravando no SQLite local, que se perde quando o Render reinicia. Reinicie o serviço depois de conferir o Neon." Sem citar specs.
- `app/main.py` passa a chamar o diagnóstico novo; o antigo sai de `app/database.py`.
- Nenhuma chamada a `app.database.get_connection` fora de `app/database.py` e de `app/banco.py` (o fallback).

## Critérios de aceite
- [ ] O arquivo `tests/test_aceite_077c.py` prova que `app.banco.diagnostico()` responde `tipo = "Postgres"` com o backend Postgres, sem expor a `DATABASE_URL`, e que `verificar_banco` fica OK com Postgres e em Atenção, sem citar "073 a 076", na queda para SQLite.
