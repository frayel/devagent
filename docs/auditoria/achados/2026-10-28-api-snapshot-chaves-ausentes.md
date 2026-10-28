---
id: 2026-10-28-api-snapshot-chaves-ausentes
severidade: media
painel: varios
status: aberto
visto_em: 2026-10-28T01:10-03:00
---

# /api/snapshot omite as chaves fonte e coletado_em em diversos painéis

## O que o investidor vê
Ao consumir a API `/api/snapshot`, diversos objetos dentro de `paineis` (como `divergencia_ibov_dolar`, `sensibilidade_juros` e `correlacao_di`) não expõem as chaves `fonte` ou `coletado_em`.

## O que deveria ver
Conforme o contrato de auditoria (`auditoria/README.md`), todas as entradas válidas de painéis no dicionário `paineis` da resposta JSON precisam expor, obrigatoriamente, as chaves `fonte` e `coletado_em`. Alguns usam nomes como `time` ou `timestamp` em vez do padrão.

## Evidência
Consultando o endpoint:
`curl -s 'https://devagent-vb52.onrender.com/api/snapshot' | jq -r '.paineis.correlacao_di'`
retorna:
```json
{
  "correlacao_intradiaria": -0.24062694014056735,
  "correlacao_5d": -0.9594756756060249,
  "status_intradiaria": "Descolado",
  "status_5d": "Correlacionado",
  "time": "27/10/2026 19:58:53 BRT",
  "fonte": "mt5"
}
```
(omite `coletado_em`). E para `divergencia_ibov_dolar` não há `fonte` e usa `timestamp`.

## Como reproduzir
1. Realize requisição GET para `https://devagent-vb52.onrender.com/api/snapshot`.
2. Observe a ausência das chaves padrão `fonte` e `coletado_em` nos objetos listados sob a propriedade `paineis`.

## Invariante proposta
Verificar no auditor determinístico se todas as chaves sob `paineis` que sejam objetos no JSON de `/api/snapshot` contêm `fonte` e `coletado_em` não nulos.
