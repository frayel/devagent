---
id: 077a
titulo: Resíduos do SQLite depois da migração (consultor, diagnóstico do banco e dois painéis)
status: ready
esforco: M
gaveta: saúde técnica
aceite: tests/test_aceite_077a.py, tests/test_aceite_migracao_snapshots.py
tabelas_legadas: radar_anomalia_fechamento_cache, consultor_confianca_regras
---

## Problema

Esta spec não é uma divisão da 077. Ela leva o sufixo `a` só para entrar na fila logo depois da 077, que já está em implementação, e antes das 078 a 083.

As specs 073a a 076b levaram os painéis para o Postgres, e a produção está nele (`GET /api/coleta` responde `"banco": "postgres"` em 23/10/2026). Ficaram três restos da época do SQLite:

1. **Consultor quebrado no Postgres.** `app/services/consultor_opinioes.py` recebe a conexão do Postgres por `app.consultor.armazenamento.get_connection`, mas manda SQL de SQLite: placeholder `?` e `INSERT OR REPLACE`. Em 23/10 o último erro da coleta era `consultor_opinioes: the query has 0 placeholders but 1 parameters were passed`. A tabela `consultor_llm_uso` nem existe no Postgres. Resultado: a cota do Gemini não é contada, a fila de matérias não anda e as opiniões das casas não chegam ao Consultor.
2. **Página /sistema mede o banco errado.** `app/database.py::diagnostico()` (spec 082) crava `"tipo": "SQLite"`, conta tabelas e mede o tamanho do `data.db`, sem perguntar a `app/banco.py` qual backend está ativo. Com `DATABASE_URL` configurado, `verificar_banco()` mostra em Atenção "a aplicação ainda grava no SQLite local... A troca para o Postgres está nas specs 073 a 076". É falso positivo, e o ciclo de saúde de produção (ADR 016) lê essa página para decidir o que corrigir.
3. **Dados que ainda somem a cada reinício.** Continuam gravando e lendo direto no SQLite, que o Render apaga ao reiniciar:
   - Radar de Anomalia no Fechamento: `save_radar_anomalia_fechamento_data` e `get_latest_radar_anomalia_fechamento_data` (tabela `radar_anomalia_fechamento_cache`);
   - confiança histórica das regras do consultor: `save_consultor_confianca_regra` e `get_consultor_confianca_regras` (tabela `consultor_confianca_regras`), calculada uma vez por semana, então um reinício na segunda zera a confiança até o sábado seguinte;
   - a contagem da fila de matérias em `app/main.py` (`fila_n`), que abre `app.database.get_connection` e conta uma tabela do SQLite que nunca recebe nada em produção.

A 077 depende de todos os dados estarem no Postgres; estes três são a parte que faltou.

## Comportamento esperado

### Consultor no Postgres
- Toda função de `app/services/consultor_opinioes.py` que recebe `backend == "postgres"` usa `%s` e sintaxe de Postgres. `INSERT OR REPLACE` em `consultor_llm_uso` vira `INSERT ... ON CONFLICT (data) DO UPDATE SET chamadas = consultor_llm_uso.chamadas + 1`.
- `app/consultor/armazenamento.py::init_db` cria `consultor_llm_uso (data DATE PRIMARY KEY, chamadas INTEGER NOT NULL)` também no ramo Postgres.
- Uma função única escolhe o placeholder pelo backend, para que o mesmo texto de SQL sirva aos dois (por exemplo `sql_para(backend, "... WHERE guid = ?")` trocando `?` por `%s` no Postgres). Os ramos duplicados `if backend == "postgres": conn.close() else: conn.close()` saem.
- Vale para `app/consultor/placar.py` e para qualquer outro módulo que use a conexão de `armazenamento`.

### Diagnóstico do banco
- `diagnostico()` muda para `app/banco.py` e descreve o backend de `get_backend_type()`:
  - Postgres: `tipo = "Postgres"`, tabelas por `SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'`, tamanho por `pg_database_size(current_database())`, latência medida na mesma conexão.
  - SQLite: o comportamento atual.
- `database_url` continua indicando se a variável existe, nunca o valor.
- `verificar_banco()` em `app/services/sistema.py`:
  - Postgres conectado: OK.
  - SQLite com `DATABASE_URL` configurado só acontece quando o Postgres não respondeu na partida (`_determine_backend` caiu para `sqlite_efemero`). Continua Atenção, com o texto: "DATABASE_URL está configurado, mas o Postgres não respondeu quando a instância subiu; a aplicação está gravando no SQLite local, que se perde quando o Render reinicia. Reinicie o serviço depois de conferir o Neon." Sem citar specs.
- `app/main.py` passa a chamar o diagnóstico novo; o antigo sai de `app/database.py`.

### Radar de Anomalia no Fechamento e confiança das regras
- O radar grava e lê por `gravar_snapshot` / `ler_snapshot` com o painel `radar_anomalia_fechamento`, como os lotes 074 a 076b. Mesmo payload, mesma fonte no rodapé.
- A confiança das regras vai para um snapshot `consultor_confianca`, com `data_referencia` do dia do cálculo e payload `{regra: {...}}`; a leitura pega o mais recente (`ler_snapshot` do último dia disponível, como já faz o histórico).
- As duas tabelas saem do `init_db` do SQLite e de todo `app/` (campo `tabelas_legadas` acima).
- `fila_n` em `app/main.py` conta `consultor_fila_materias` pela conexão de `app.consultor.armazenamento`.

## Fontes de dados

Nenhuma nova. Nenhuma requisição externa a mais.

## Cálculos

Nenhum novo. A contagem de chamadas ao Gemini volta a funcionar com a mesma regra (`GEMINI_MAX_CHAMADAS_DIA`, padrão 200).

## Critérios de aceite

- [ ] `tests/test_aceite_077a.py` passa com esta spec `done`: com uma conexão Postgres falsa, `get_llm_uso_hoje`, `incrementar_llm_uso`, `set_opinioes_status`, `get_materias_nao_processadas`, `marcar_como_processada` e `save_opiniao` não mandam `?` nem `INSERT OR`, e o número de `%s` bate com o de parâmetros.
- [ ] O mesmo arquivo prova que `app.banco.diagnostico()` responde `tipo = "Postgres"` com o backend Postgres, sem expor a `DATABASE_URL`, e que `verificar_banco` fica OK com Postgres e em Atenção, sem citar "073 a 076", na queda para SQLite.
- [ ] `tests/test_aceite_migracao_snapshots.py` passa: `radar_anomalia_fechamento_cache` e `consultor_confianca_regras` não aparecem mais em `app/`.
- [ ] Os testes do SQLite que já existem (`tests/test_consultor_opinioes.py`, `tests/test_consultor_armazenamento.py`, `tests/test_sistema.py`) continuam passando; o teste `test_banco_sqlite_com_database_url_pede_atencao` é ajustado ao texto novo, sem mudar o nível.
- [ ] Nenhuma chamada a `app.database.get_connection` fora de `app/database.py` e de `app/banco.py` (o fallback).

## Invariantes de produção

- `/api/sistema`: o item "Banco de dados" mostra `Postgres` e nível OK enquanto `/api/coleta` responde `"banco": "postgres"`.
- `/api/coleta`: `ultimo_erro` não contém `placeholders` nem `INSERT OR`.
- `/consultor`: depois de um dia de pregão com `GEMINI_API_KEY` configurada, a seção de opiniões das casas não fica vazia por erro de banco, e o status das opiniões não fica em erro com mensagem do psycopg.
- Depois de um reinício do Render, o Radar de Anomalia no Fechamento continua mostrando o último dado gravado, e a confiança das regras no Consultor não volta a "sem histórico".

## Fora do escopo

- Apagar as demais tabelas mortas do `init_db` do SQLite (`historico_diario_cache`, `ibovespa_cache`, `highlights_cache`, `instrumentacao_*` e as cópias SQLite das tabelas do consultor). Fica para uma rodada de manutenção, depois desta.
- Migrar os dados que hoje estão no SQLite efêmero de produção: eles se perdem no próximo reinício de qualquer forma. O radar e a confiança se refazem na próxima coleta e no próximo sábado.
- Trocar o fallback para SQLite por falha imediata quando o Postgres não responde na partida.
- Qualquer mudança na 077 (congelamento) ou na 078 (cinco pregões).
