---
id: 168
titulo: O banco local só cria as tabelas que o app usa
status: ready
esforco: P
gaveta: poda
aceite: tests/test_aceite_168.py
revisada: 2026-11-17
origem: Tabela `instrumentacao_coleta_tempo`
---

## Problema
Que tabelas do banco ainda servem para alguma coisa?

O backlog apontava uma: `instrumentacao_coleta_tempo`, que ninguém grava desde a spec 152. Medido em 17/11, são cinco. `app/database.py:init_db` (linhas 266 a 369) cria no SQLite local, em toda subida do app e em todo teste, as cinco tabelas que a spec 073b migrou para `snapshots_paineis`/`series_diarias` e prometeu apagar ("as tabelas antigas desses cinco somem de `app/database.py`"), mas que ficaram:

| Tabela | Substituída por | Leituras ou gravações em `app/` fora do `init_db` |
|---|---|---|
| `historico_diario_cache` | `series_diarias` (`save_historico_diario` grava por `gravar_serie`) | 0 |
| `instrumentacao_coleta_vazia` | snapshot `instrumentacao` | 0 |
| `instrumentacao_coleta_tempo` | snapshot `instrumentacao` | 0 |
| `ibovespa_cache` | snapshot `ibovespa` | 0 |
| `highlights_cache` | snapshot `highlights` | 0 |

Medida: `grep -rEoh "(FROM|INTO|UPDATE|JOIN)\s+<tabela>\b" app --include=*.py`. As duas ocorrências de `ibovespa_cache` e de `highlights_cache` são as sondas de migração do próprio `init_db` (`SELECT fonte FROM ibovespa_cache LIMIT 1` e afins, linhas 318 a 357), que existem só para acrescentar colunas a tabelas que ninguém lê. Junto vão quatro índices (`idx_instrumentacao_coleta_vazia_timestamp`, `idx_instrumentacao_coleta_tempo_timestamp`, `idx_ibovespa_cache_timestamp`, `idx_highlights_cache_timestamp`), cujos comentários ainda dizem otimizar `get_latest_ibovespa_data()` e `get_latest_highlights_data()`, que hoje leem o snapshot.

O custo é de leitura, não de máquina: quem abre o `init_db` acha que o Ibovespa e os destaques vivem nessas tabelas, e o `docs/STATE.md` diz o mesmo (linhas 308, 338, 578, 584, 589 e 595).

## Comportamento esperado
1. **`init_db()`** (`app/database.py`) deixa de criar as cinco tabelas e os quatro índices acima e perde as quatro sondas de migração (`try: SELECT ... except sqlite3.OperationalError: ALTER TABLE ...`) de `ibovespa_cache` e `highlights_cache`. Continua igual o resto: a chamada a `app.banco.init_db` com o retorno em `DBInacessivelError`, as tabelas do Consultor (`consultor_fila_materias` com o `ALTER` de `processada`, `consultor_opinioes`, `consultor_opinioes_status`, `consultor_llm_uso`), `criar_tabelas_consenso_yahoo(conn)`, o `commit` e o `close`.
2. **Sem `DROP TABLE`.** Um `data.db` antigo que já tenha as cinco tabelas fica com elas; o app só para de criá-las. Em produção o banco é o Postgres, onde elas nunca existiram (`app/banco.py:init_db` cria só `snapshots_paineis`, `series_diarias` e as do próprio módulo); o SQLite de produção é efêmero e nasce de novo a cada deploy.
3. **Testes que citam as tabelas:**
   - `tests/test_avaliador_historico.py:10`, `cursor.execute("DELETE FROM historico_diario_cache")`, sai: com a tabela inexistente ele levanta `sqlite3.OperationalError`. O banco do teste já nasce vazio a cada teste (`tests/conftest.py`, `setup_db` com `tmp_path`), então a limpeza não fazia nada. As asserções do arquivo não mudam.
   - `tests/test_instrumentacao_coleta_tempo.py:30`, o `if "instrumentacao_coleta_tempo" in query:` do cursor falso, sai, e `fake_execute` passa a guardar toda chamada (`salvos.append((query, params))`). A lista `salvos` nunca foi conferida; nenhuma asserção muda.
4. **Contrato novo**, ao lado do que já existe em `tests/test_database_tabelas.py` (toda tabela gravada é criada): toda tabela criada é lida ou gravada. Fica no teste de aceite desta spec.

## Fontes de dados
Nenhuma. Plano B não se aplica: nenhuma tela lê as tabelas que saem.

## Cálculos
Exemplo de ponta a ponta, num SQLite novo (`DATABASE_PATH` apontando para um arquivo inexistente, sem `DATABASE_URL`), depois de `app.database.init_db()`:

- Hoje, `SELECT name FROM sqlite_master WHERE type = 'table'` devolve 15 nomes: `consultor_consenso_yahoo`, `consultor_consenso_yahoo_status`, `consultor_fila_materias`, `consultor_llm_uso`, `consultor_opinioes`, `consultor_opinioes_status`, `highlights_cache`, `historico_diario_cache`, `ibovespa_cache`, `instrumentacao_coleta_tempo`, `instrumentacao_coleta_vazia`, `series_diarias`, `simbolos_sem_cotacao`, `snapshots_paineis` e `sqlite_sequence`.
- Depois, 10: os mesmos menos as cinco tabelas legadas. `sqlite_sequence` continua, porque as tabelas do Consultor usam `AUTOINCREMENT`.
- O diagnóstico do banco (`app/banco.py:diagnostico`, modo `sqlite_efemero`) conta `type = 'table'` com `sqlite_sequence`: o detalhe do item de banco em `/sistema` passa de `15 tabelas · ...` para `10 tabelas · ...` num SQLite novo. Em produção (Postgres) a contagem não muda.

## Critérios de aceite
- [ ] `tests/test_aceite_168.py`, com `exigir_spec_done("168")`:
  - depois de `init_db()` num SQLite temporário (o `setup_db` do `conftest.py` já faz isso), `sqlite_master` não tem nenhuma das cinco tabelas nem dos quatro índices citados no *Problema*, e tem exatamente os 10 nomes do exemplo;
  - **toda tabela é usada:** para cada nome de `sqlite_master` com `type = 'table'`, menos `sqlite_sequence`, algum arquivo `.py` de `app/` casa com a regex `(FROM|INTO|UPDATE|JOIN)\s+<nome>\b`. Uma tabela nova que só é criada reprova o teste; uma tabela legada de volta também;
  - o código-fonte de `app/` (todos os `.py`) não contém nenhum dos cinco nomes de tabela.
- [ ] `tests/test_database_tabelas.py`, `tests/test_avaliador_historico.py`, `tests/test_instrumentacao_coleta_tempo.py`, `tests/test_concentracao_ordens.py` e o resto do `make verify` continuam verdes, sem mudar asserção.
- Arquivos tocados: `app/database.py`, `tests/test_avaliador_historico.py`, `tests/test_instrumentacao_coleta_tempo.py` e o novo `tests/test_aceite_168.py`. Medido com `grep -rlwE "highlights_cache|ibovespa_cache|historico_diario_cache|instrumentacao_coleta_tempo|instrumentacao_coleta_vazia" app tests`: 1 de código e 2 de teste. O `docs/STATE.md` e o `CHANGELOG.md` são atualizados na entrega, como em todo PR: as seis linhas do `STATE.md` que dão essas tabelas como armazenamento atual passam a citar o snapshot.

## Invariantes de produção
- `/`, `/consultor`, `/sistema` e `/api/snapshot` respondem como antes do deploy: Ibovespa, destaques e instrumentação seguem vindo dos snapshots (a contagem de `paineis` em `/api/snapshot` não muda).
- `GET /api/sistema` (com a senha), item do banco: em Postgres, o número de tabelas não muda com o deploy.
- Nenhum erro `no such table` nos logs do serviço depois do deploy.

## Fora do escopo
- `DROP TABLE` em bancos que já tenham as tabelas (ver item 2 do *Comportamento esperado*).
- As tabelas do Consultor no SQLite local: elas são lidas (`app/main.py:689` e `:923` contam `consultor_fila_materias` por `app.database.get_connection`). Se essas leituras deviam ir ao Postgres é outra pergunta; está no relatório desta sessão para o desenvolvimento.
- Dar asserção a `test_agendador_registra_tempo` (`tests/test_instrumentacao_coleta_tempo.py`), que termina em `pass`: depende do relógio para saber quais coletores rodam e ficou no backlog ("O teste do agendador confere a rodada").
- Juntar as ~105 funções `save_*`/`get_*` de `app/database.py` num registro declarativo: é o item "Radares do snapshot num laço" do backlog.
