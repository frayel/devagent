# Diário do auditor

Memória entre execuções do auditor LLM. No máximo 20 linhas: condense em vez de acumular.

- 2026-10-02 · Auditoria determinística sem falhas. Painel de dispersão viola a especificação matemática (Spec 004). Fuso BRT faltando.
- 2026-10-03 · Identificada regressão na formatação de fuso (BRT ausente/formato reduzido) nos painéis Força Relativa e Escudo contra Quedas.
- 2026-10-06 · Constatada ausência sistemática de rodapés completos (falta fonte, data, BRT) no HTML e dados incompletos (`fonte`, `coletado_em`) na `/api/snapshot` para painéis recentes.
- Pendente: checar a precisão dos cálculos com fontes independentes em horário de pregão ativo.
