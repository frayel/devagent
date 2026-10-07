---
id: 2026-10-06-api-snapshot-falta-fonte
severidade: media
painel: multiplos
status: resolvido
visto_em: 2026-10-06T01:50-03:00
---

# /api/snapshot falhando em prover fonte e data para novos painéis

## O que o investidor vê
Ao consumir a API `/api/snapshot`, os painéis `atrasadas_rally`, `armadilha_abertura` e `sobrevivencia_semanal` não expõem as chaves `fonte` ou `coletado_em`.

## O que deveria ver
Conforme o contrato de auditoria, todas as entradas válidas de painéis no dicionário `paineis` da resposta JSON precisam expor, obrigatoriamente, as chaves `fonte` e `coletado_em`.

## Evidência
Comando executado: `curl -s https://devagent-vb52.onrender.com/api/snapshot | jq '.paineis | keys'` e verificação detalhada. A API retorna os novos painéis mas não fornece metadados neles.

## Como reproduzir
1. Realize requisição GET para `https://devagent-vb52.onrender.com/api/snapshot`.
2. Observe que as propriedades `fonte` e `coletado_em` estão ausentes ou vazias para os painéis citados.

## Invariante proposta
Verificar se todas as chaves sob `paineis` no JSON de `/api/snapshot` contêm `fonte` e `coletado_em` não nulos.

**Atualização (06/10/2026):** A invariante foi codificada e testada com sucesso na API de produção. Nenhum painel atual deixa de exibir as chaves `fonte` e `coletado_em` no snapshot.
