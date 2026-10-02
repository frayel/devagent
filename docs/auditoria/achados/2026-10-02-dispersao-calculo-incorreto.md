---
id: 2026-10-02-dispersao-calculo-incorreto
severidade: media
painel: dispersao
status: aberto
visto_em: 2026-10-02T01:05-03:00
---

# Painel de Dispersão calcula a proporção em relação ao total, ignorando a especificação

## O que o investidor vê
No painel "Termômetro de Dispersão", consta "65% em alta". O texto abaixo indica: "65 subiram vs 31 caíram (amostra de 100 ações)". 65 / (65+31) resultaria em 67,7%, porém o sistema apresenta 65%, sugerindo que está dividindo por 100.

## O que deveria ver
A Spec 004 instrui expressamente: `Calcular a proporção: Ações_em_Alta / (Ações_em_Alta + Ações_em_Baixa) * 100`. Ou seja, as neutras deveriam ser descartadas do divisor, resultando em algo próximo de 67,7%.

## Evidência
No retorno da `/api/snapshot`:
```json
      "dispersao": {
        "em_alta": 65,
        "em_baixa": 31,
        "proporcao_alta_pct": 65.0
      }
```

## Como reproduzir
Acessar `https://devagent-vb52.onrender.com/` ou consultar `/api/snapshot` e comparar a variável `proporcao_alta_pct` em face à quantidade `em_alta` + `em_baixa`.

## Invariante proposta
Verificar no auditor determinístico se `proporcao_alta_pct == em_alta / (em_alta + em_baixa) * 100` (respeitada uma pequena tolerância).
