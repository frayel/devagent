# Diário do auditor

Memória entre execuções do auditor LLM. No máximo 20 linhas: condense em vez de acumular.

- 2026-10-10 a 2026-10-30 · Problemas antigos resolvidos. Produção corrigida após inatividade (HTTP 500) e implementada invariante `api.contrato_chaves`.
- 2026-11-03 a 2026-11-05 · Maré do mercado exibia componente Calma zerado no dia 3, mas foi resolvido no dia 5.
- 2026-11-06 · Encontradas 2 falhas ao auditar (2026-11-06 22:20):
  - A última coleta do Ibovespa foi em 2026-11-04, faltando o último pregão esperado de 2026-11-06 (`ibov.coleta_do_ultimo_pregao`).
  - O gráfico do Ibovespa também termina em 2026-11-04, faltando o pregão mais recente (`ibov.historico_atual`). Reportados achados `2026-11-06-ibov-coleta-do-ultimo-pregao.md` e `2026-11-06-ibov-historico-atual.md`.
