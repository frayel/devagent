---
id: 053
titulo: Relógio de Volatilidade Intraday
status: done
esforco: G
---

## Problema
Em qual horário o mercado esteve mais errático hoje? O investidor quer saber os picos de indecisão.

## Comportamento esperado
Ao invés do volume, mapeia as amplitudes de preço hora a hora para encontrar os picos de indecisão.

## Fontes de dados
brapi

## Cálculos
Mapeia as amplitudes de preço hora a hora para encontrar os picos de indecisão.

## Critérios de aceite
- [ ] O endpoint de mock HTTP valida que a resposta extrai corretamente a amplitude.
- [ ] A chave `relogio_volatilidade` com o status textual e as métricas está presente na rota `api/snapshot`.
- [ ] A interface exibe o painel de Relógio de Volatilidade Intraday.

## Invariantes de produção
- A chave `relogio_volatilidade` deve existir.

## Fora do escopo
- Acompanhar mercados europeus ou asiáticos, DXY, commodities.
