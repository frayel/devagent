# Relatório de Execução: Spec 084 (Consultor no Postgres)
Data: 2026-10-24

## Decisões Tomadas
- Adicionada a criação da tabela `consultor_llm_uso` e coluna `processada` em `consultor_fila_materias` no ramo Postgres de `app/consultor/armazenamento.py`.
- Atualizado SQLite `init_db()` para incluir `processada` no `CREATE TABLE` e capturar a adição dinâmica `ALTER TABLE ADD COLUMN`.
- Atualizadas as funções `get_llm_uso_hoje` e `incrementar_llm_uso` em `app/services/consultor_opinioes.py` para usar fuso horário de BRT (`datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=-3)))`), assim a cota renova-se à meia-noite brasileira.
- O bloco de inicialização (chamadas ao banco de dados e limites da cota) em `extrair_opinioes` foi envolto em blocos `try/except Exception` que registram o erro via `set_opinioes_status('erro', ...)`.
- Erros em `set_opinioes_status()` dentro da exceção original foram apanhados passivamente usando `logger.error` para não quebrarem o agendador, preservando resiliência.
- O status da spec 084 foi alterado para `done`, e os artefatos `CHANGELOG.md` e `docs/STATE.md` atualizados.
