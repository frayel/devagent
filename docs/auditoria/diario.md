# Diário do auditor

Memória entre execuções do auditor LLM. No máximo 20 linhas: condense em vez de acumular.

- 2026-10-02 · Auditoria determinística sem falhas. Painel de dispersão viola a especificação matemática (Spec 004). Fuso BRT faltando.
- 2026-10-03 · Identificada regressão na formatação de fuso (BRT ausente/formato reduzido) nos painéis Força Relativa e Escudo contra Quedas.
- 2026-10-06 · A invariante de rodapés e metadados no `/api/snapshot` foi automatizada em `auditar.py`. Alguns painéis antigos foram corrigidos pelo dev, mas Concentração Setorial e Volatilidade Silenciosa continuam falhando na formatação da data do rodapé.
- 2026-10-08 · Auditoria determinística limpa (24 checagens verdes). O problema com 'Concentração Setorial' e 'Volatilidade Silenciosa' foi resolvido. A fonte independente confirmou a veracidade do Ibovespa (erro <0.01%).
- Pendente: acompanhar o painel de dispersão que violava spec se há reincidência, ou testar cruzamentos mais complexos com MT5.
