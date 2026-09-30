---
id: 2026-09-30-radar-volume-anormal-ausente
severidade: alta
painel: alertas_volume_anormal
status: resolvido
visto_em: 2026-09-30T00:50:00-03:00
---

# Painel "Radar de Volume Anormal" ausente na produção e no snapshot da API

## O que o investidor vê
Ao acessar a página inicial do Painel B3, não há nenhum painel com o nome "Radar de Volume Anormal". A chamada à API de contrato em `/api/snapshot` não retorna a chave correspondente (por exemplo, `"radar_volume"` ou similar).

## O que deveria ver
O usuário deveria visualizar na página inicial o card "Radar de Volume Anormal", listando os ativos com volume acima de sua média móvel de volume.
Além disso, a API `/api/snapshot` deveria expor esse novo painel seguindo o contrato de invariante especificado na Spec 005.

## Evidência
Requisição executada em produção (`https://devagent-vb52.onrender.com/api/snapshot`) com o jq:
```json
{
  "gerado_em": "2026-09-30T00:47:56.808826+00:00",
  "paineis": {
    "ibovespa": { ... },
    "altas_baixas": { ... }
  }
}
```
O campo dos alertas de volume, esperado pelo contrato, simplesmente não existe, mesmo o recurso já constando como `status: done` em `docs/specs/005-alertas-volume-anormal.md`.

## Como reproduzir
1. Acesse o ambiente de produção (https://devagent-vb52.onrender.com/).
2. Verifique a ausência do painel visual.
3. Chame a API com: `curl -s https://devagent-vb52.onrender.com/api/snapshot`.

## Invariante proposta
Verificar na asserção `app.snapshot_igual_tela` do auditor ou criar uma nova checagem que valide: "Se o painel for retornado pela API `api/snapshot`, ele não pode estar vazio se as regras da spec determinarem obrigatoriedade (mesmo que informando dados insuficientes), mas ele DEVE ao menos ter a chave correspondente garantida no JSON". Como o endpoint nem retornou a chave de volume, o contrato falhou.

## Resolução
Corrigido o coletor `volume_alerts.py` para salvar e persistir os resultados no banco de dados mesmo quando nenhuma ação satisfaz a condição de volume anormal (lista vazia). Isso garante a presença da chave `radar_volume` no snapshot da API, provendo os metadados corretos, e ajusta a interface no `index.html` para exibir um aviso explícito e amigável ao usuário de que não existem anomalias no momento.
