# Diário do auditor

Memória entre execuções do auditor LLM. No máximo 20 linhas: condense em vez de acumular.

- 2026-10-02 · Auditoria determinística sem falhas. Painel de dispersão viola spec. Fuso BRT faltando.
- 2026-10-03 · Identificada regressão na formatação de fuso nos painéis Força Relativa e Escudo contra Quedas.
- 2026-10-06 · A invariante de rodapés foi automatizada. Concentração Setorial e Volatilidade Silenciosa falhando.
- 2026-10-08 · Novo achado: múltiplos painéis falhando na coleta exibem "Dado indisponível agora", mas o rodapé fica malformado ("Fonte  · ") sem fonte ou data de tentativa.
- 2026-10-10 · Auditoria limpa (24 checagens). Problema do rodapé em painéis vazios resolvido (parcialmente).
- 2026-10-13 · Auditoria limpa. Constatado que o defeito de rodapés "Fonte  · " em painéis vazios persiste em produção. Achado reportado novamente.
- 2026-10-14 · Auditoria determinística impecável (25 checagens). O defeito anterior (`Fonte  · `) não ocorre mais. Contudo, detectou-se um novo problema onde o rodapé omite o sufixo " BRT" em determinados painéis (ex. *Scanner de Capitulação*), sendo classificado como achado de severidade média.
- Pendente: A próxima execução deve certificar se o novo bug de formatação "BRT" foi corrigido e testar os painéis sob estresse de pregão aberto.
