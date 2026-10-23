---
id: 077d
titulo: Resíduos do SQLite depois da migração (Dois painéis em snapshots)
status: ready
esforco: P
gaveta: saúde técnica
aceite: tests/test_aceite_077d.py
tabelas_legadas: radar_anomalia_fechamento_cache, consultor_confianca_regras
---

## Problema

O Radar de Anomalia no Fechamento e a confiança histórica das regras do consultor continuam gravando e lendo direto no SQLite, que o Render apaga ao reiniciar.

## Comportamento esperado

### Radar de Anomalia no Fechamento e confiança das regras
- O radar grava e lê por `gravar_snapshot` / `ler_snapshot` com o painel `radar_anomalia_fechamento`, como os lotes 074 a 076b. Mesmo payload, mesma fonte no rodapé.
- A confiança das regras vai para um snapshot `consultor_confianca`, com `data_referencia` do dia do cálculo e payload `{regra: {...}}`; a leitura pega o mais recente (`ler_snapshot` do último dia disponível, como já faz o histórico).
- As duas tabelas saem do `init_db` do SQLite e de todo `app/` (campo `tabelas_legadas` acima).

## Critérios de aceite
- [ ] `tests/test_aceite_077d.py` passa: `radar_anomalia_fechamento_cache` e `consultor_confianca_regras` não aparecem mais em `app/`.
