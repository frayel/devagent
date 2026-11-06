# Diário do auditor

Memória entre execuções do auditor LLM. No máximo 20 linhas: condense em vez de acumular.

- 2026-10-10 a 2026-10-28 · Problemas antigos resolvidos (0 falhas). Achado de contrato do snapshot reportado e resolvido logo em seguida.
- 2026-10-29 a 2026-10-30 · Produção corrigida após inatividade (HTTP 500) e implementada invariante `api.contrato_chaves`. Sem falhas reportadas.
- 2026-11-03 a 2026-11-05 · Maré do mercado exibia componente Calma zerado no dia 3, mas foi resolvido no dia 5.
- 2026-11-06 · Encontrada falha ao auditar: a última coleta do Ibovespa foi em 2026-11-04, faltando o último pregão esperado de 2026-11-05. Reportado novo achado `2026-11-06-ibov-coleta-do-ultimo-pregao.md`.
