# Diário do auditor

Memória entre execuções do auditor LLM. No máximo 20 linhas: condense em vez de acumular.

- 2026-10-02 · Auditoria determinística sem falhas. Painel de dispersão viola spec. Fuso BRT faltando.
- 2026-10-03 · Identificada regressão na formatação de fuso nos painéis Força Relativa e Escudo contra Quedas.
- 2026-10-06 · A invariante de rodapés foi automatizada. Concentração Setorial e Volatilidade Silenciosa falhando.
- 2026-10-08 · Auditoria determinística limpa. O problema dos rodapés normais foi resolvido. Fonte confirmou Ibovespa (erro <0.01%).
- 2026-10-08 · Novo achado: múltiplos painéis falhando na coleta exibem "Dado indisponível agora", mas o rodapé fica malformado ("Fonte  · ") sem fonte ou data de tentativa.
- 2026-10-10 · Auditoria limpa (24 checagens). Problema do rodapé em painéis vazios resolvido (parcialmente).
- 2026-10-13 · Auditoria limpa. Constatado que o defeito de rodapés "Fonte  · " em painéis vazios persiste em produção. Achado reportado novamente (status: aberto).
- 2026-10-15 · Auditoria limpa (26 checagens). Bug do rodapé fantasma extinto em produção.
- Pendente: checar integridade de dados e confirmar se há novos painéis com problemas semelhantes de tratamento de erro.
