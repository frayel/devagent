---
id: 2026-11-06-ibov-coleta-do-ultimo-pregao
severidade: media
painel: ibovespa
status: aberto
visto_em: 2026-11-06T01:49:49+00:00
---

# Última coleta do Ibovespa feita em pregão anterior ao mais recente

## O que o investidor vê
A página inicial mostra que a última coleta de dados do Ibovespa foi realizada no dia 2026-11-04, no entanto o último pregão esperado (mais recente) é o do dia 2026-11-05. A coleta para o dia 2026-11-05 não foi realizada.

## O que deveria ver
Os dados no painel deveriam refletir as coletas feitas para o dia de pregão mais recente que, neste caso, é 2026-11-05, acompanhando o mundo no ritmo prometido.

## Evidência
Do relatório de auditoria `/tmp/auditoria/relatorio.json`:
```json
    {
      "id": "ibov.coleta_do_ultimo_pregao",
      "status": "falha",
      "titulo": "Última coleta feita no pregão mais recente",
      "detalhe": "coleta em 2026-11-04; pregão esperado 2026-11-05",
      "evidencia": {}
    }
```

## Como reproduzir
1. Navegue para a página inicial em https://devagent-vb52.onrender.com/
2. Observe a data do último pregão listada para o painel Ibovespa, ou execute `make audit ARGS="--navegador --saida /tmp/auditoria"` e observe a falha da checagem `ibov.coleta_do_ultimo_pregao`.

## Invariante proposta
Já aplicada na checagem `ibov.coleta_do_ultimo_pregao` do auditor de produção.
