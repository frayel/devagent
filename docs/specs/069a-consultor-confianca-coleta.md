---
id: 069a
titulo: Consultor confiança · coleta de histórico longo e cálculos do histórico de cada regra
status: done
esforco: M
---

## Problema
O `PRODUTO.md` exige grau de confiança em toda recomendação. Para isso, o consultor precisa de um histórico extenso (2 anos) de cotações de todos os ativos analisados para que possamos testar as regras de decisão em pregões passados e calcular seu índice de acerto.

## Comportamento esperado
- Um novo cron/coletor roda no fim de semana para buscar o histórico de 2 anos (`range=2y`) de cada ativo do universo de cobertura do consultor e do `^BVSP`, com cache no SQLite.
- O MT5 é preferencial (entrega 300 barras), com o `chart` do Yahoo Finance como reserva para 2 anos.
- Um serviço processa as séries de 2 anos e avalia, em cada pregão (t) onde já se tenham pelo menos 220 pregões, todas as regras sem viés de futuro.
- Uma linha no banco de dados guarda por regra a contagem total de vezes que disparou (n), a taxa de acertos e o excesso mediano, com base no retorno 20 pregões à frente.
- O histórico calculável deve ser cacheado semanalmente para consumo da API do consultor.

## Critérios de aceite
- [ ] O banco de dados passa a incluir uma tabela que armazena os cálculos sumarizados de confiança de cada regra do consultor.
- [ ] Um teste garante o funcionamento da coleta extensa sem estourar tempo ou limites, cobrindo o fallback de Yahoo para brapi e MT5.
- [ ] Um teste usa um fixture sintético (onde R5 dispara 3 vezes e os retornos são controlados) e assegura que o número de ocorrências, taxa de acertos e excesso mediano batem exatamente com as métricas esperadas.
- [ ] Um teste comprova ausência de look-ahead bias: mudar o preço de "t+1" ou dianteiras não deve afetar a avaliação registrada no pregão "t".
- [ ] Eventos a menos de 20 pregões do fim da série não entram na contagem.

## Fora do Escopo
- Alterações na UI ou no endpoint de consumo final (ficará para a spec 069b).
- Custos de corretagem e impostos no backtest.
- Otimização das regras baseada no histórico.
