# Diário do auditor

Memória entre execuções do auditor LLM. No máximo 20 linhas: condense em vez de acumular.

- 2026-10-10 a 2026-10-21 · Problemas de rodapés, 'clima_global' e 'detector_acao_orfa' resolvidos.
- 2026-10-22 a 2026-10-23 · Auditoria e inspeção exploratória passaram. Achado do rodapé incompleto (fuso horário) resolvido.
- 2026-10-26 · Auditoria determinística falhou em `ibov.variacao_plausivel` (-13.88% vs limite ±12.0%). Fonte (Yahoo Finance) está retornando variação irreal (queda muito além do circuit breaker) para `^BVSP`. Achado de severidade alta reportado. Próxima checagem: avaliar normalização da fonte ou necessidade de ignorar pregões anômalos.
