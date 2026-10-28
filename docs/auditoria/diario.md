# Diário do auditor

Memória entre execuções do auditor LLM. No máximo 20 linhas: condense em vez de acumular.

- 2026-10-10 a 2026-10-23 · Problemas de rodapés, fuso horário, 'clima_global' e 'detector_acao_orfa' resolvidos.
- 2026-10-26 a 2026-10-28 · Achado da variação implausível do Ibovespa resolvido (0 falhas no determinístico em 27/10).
- 2026-10-28 · Inspeção do `/api/snapshot` encontrou o contrato quebrado para alguns painéis (falta `fonte` e `coletado_em`). Achado reportado. Próxima checagem: avaliar normalização de todas as chaves em `paineis` que sejam arrays.
