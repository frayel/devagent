# Relatório de Execução - Spec 073b

## O que foi feito
- Migramos o Ibovespa, Highlights e Instrumentação para a tabela `snapshots_paineis`.
- Migramos as séries diárias para a tabela `series_diarias`.
- Substituímos as antigas funções de salvamento/leitura (`save_ibovespa_data`, `save_highlights_data`, `get_latest_ibovespa_data`, etc) no `app/database.py` por equivalentes do `app/banco.py`.
- Lógica de banco unificada sem impactar o resto do sistema.
- Execução aprovada pelos testes.

## Decisões
- Os dados do `historico_diario_cache` (que eram um JSON enorme) foram desmembrados em barras avulsas salvas via `gravar_serie`, e na leitura (`get_historico_diario`) remontamos uma estrutura igual ao spark-line do yfinance para que a compatibilidade fosse mantida.
- Os testes rodam no db provisório criado pelo `conftest.py`, por isso garantimos que `app.banco.init_db()` seja invocado no startup do pytest.
- Como esta spec é `saúde técnica`, o contador de manutenção não foi incrementado de acordo com a regra.
