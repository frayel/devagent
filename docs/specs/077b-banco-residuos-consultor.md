---
id: 077b
titulo: Resíduos do SQLite depois da migração (Consultor no Postgres)
status: done
esforco: P
gaveta: saúde técnica
aceite: tests/test_aceite_077b.py
---

## Problema

As specs 073a a 076b levaram os painéis para o Postgres, e a produção está nele. Ficaram restos da época do SQLite. O primeiro é o Consultor quebrado no Postgres: `app/services/consultor_opinioes.py` recebe a conexão do Postgres, mas manda SQL de SQLite: placeholder `?` e `INSERT OR REPLACE`. A tabela `consultor_llm_uso` nem existe no Postgres. Resultado: a cota do Gemini não é contada, a fila de matérias não anda e as opiniões das casas não chegam ao Consultor.

## Comportamento esperado

### Consultor no Postgres
- Toda função de `app/services/consultor_opinioes.py` que recebe `backend == "postgres"` usa `%s` e sintaxe de Postgres. `INSERT OR REPLACE` em `consultor_llm_uso` vira `INSERT ... ON CONFLICT (data) DO UPDATE SET chamadas = consultor_llm_uso.chamadas + 1`.
- `app/consultor/armazenamento.py::init_db` cria `consultor_llm_uso (data DATE PRIMARY KEY, chamadas INTEGER NOT NULL)` também no ramo Postgres.
- Uma função única escolhe o placeholder pelo backend, para que o mesmo texto de SQL sirva aos dois (por exemplo `sql_para(backend, "... WHERE guid = ?")` trocando `?` por `%s` no Postgres). Os ramos duplicados `if backend == "postgres": conn.close() else: conn.close()` saem.
- Vale para `app/consultor/placar.py` e para qualquer outro módulo que use a conexão de `armazenamento`.
- A contagem de chamadas ao Gemini volta a funcionar com a mesma regra.
- `fila_n` em `app/main.py` conta `consultor_fila_materias` pela conexão de `app.consultor.armazenamento`.

## Fontes de dados e Cálculos
Nenhuma nova.

## Critérios de aceite
- [x] `tests/test_aceite_077b.py` passa com esta spec `done`: com uma conexão Postgres falsa, `get_llm_uso_hoje`, `incrementar_llm_uso`, `set_opinioes_status`, `get_materias_nao_processadas`, `marcar_como_processada` e `save_opiniao` não mandam `?` nem `INSERT OR`, e o número de `%s` bate com o de parâmetros.
