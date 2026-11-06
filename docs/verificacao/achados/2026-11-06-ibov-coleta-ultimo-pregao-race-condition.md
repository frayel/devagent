---
id: 2026-11-06-ibov-coleta-ultimo-pregao-race-condition
severidade: alta
painel: ibovespa
status: aberto
visto_em: 2026-11-06T00:00-03:00
pr: 770
---

# Correção de race condition de coletas por hibernação não resolveu coleta desatualizada do Ibovespa

## O que acontece
O PR 770, que declarou "fix: resolver race condition de coletas por hibernacao", foi submetido com o objetivo de corrigir a falha de produção `#764` (Produção incorreta: ibov.coleta_do_ultimo_pregao), onde a última coleta feita é de um pregão anterior ao esperado. Entretanto, a aplicação em produção continua gerando `ibov.coleta_do_ultimo_pregao` como falha. A auditoria diária e as verificações mostram que o sistema ainda espera a coleta do dia 2026-11-05 mas a mais recente gravada foi em 2026-11-04, indicando que a resolução da race condition não tratou o problema da coleta ser gravada no dia correto sob certas condições, ou não garantiu a coleta do pregão de referência no momento de despertar.

## O que deveria acontecer
O Ibovespa deveria reportar a última coleta efetuada para o pregão mais recente, garantindo que o `app/agendador.py` e o banco persistam a coleta sob a `data_referencia` do último pregão fechado (ou corrente) esperado pela checagem. A solução para hibernação deveria despertar, tentar e salvar com sucesso.

## Evidência
Comando `make audit ARGS="--saida /tmp/auditoria"` ainda relata a seguinte falha, idêntica ao que motivou o PR 770:
```
❌ | ibov.coleta_do_ultimo_pregao Última coleta feita no pregão mais recente | coleta em 2026-11-04; pregão esperado 2026-11-05
```

## Como reproduzir
1. Analise o estado do github executando `python -m devagent.estado_github`.
2. Observe que a checagem `#764` na auditoria de saúde continua como pendente no repositório.
3. Rode a auditoria `make audit` para confirmar.
