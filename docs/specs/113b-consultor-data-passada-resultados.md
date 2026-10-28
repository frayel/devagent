---
id: 113b
titulo: Consultor numa data passada (resultados e coleta diária)
status: done
esforco: P
gaveta: saúde técnica
aceite: tests/test_aceite_113b.py
revisada: 2026-10-24
---

## Problema
O Consultor precisa medir a qualidade das suas recomendações do passado.
O diário (`consultor_recomendacoes`) só é gravado quando alguém abre a página. Dias sem visita não têm registro.

## Comportamento esperado
- **Resultado depois do fato.** Para cada recomendação de um pregão passado, a tabela mostra a variação do ativo contra o Ibovespa nos pregões seguintes já disponíveis (até 5 pregões, o que existir), com a regra do `placar` já usada em `app/consultor/placar.py`. Se ainda não passou nenhum pregão, mostra "ainda sem resultado". O texto de amostra e janela fica no rodapé da tabela ("n = N recomendações, janela de até 5 pregões, preço de fechamento contra o IBOV").
- O coletor `consultor_fechamento` grava o diário uma vez por pregão, depois do fechamento, mesmo sem visita; fora do pregão não faz requisição externa.

## Fontes de dados
Só o banco local (`consultor_recomendacoes`, `series_diarias`). Nenhuma requisição externa.

## Cálculos
- Resultado por recomendação: `retorno_ativo(n) - retorno_ibov(n)` em pontos percentuais, com n de 1 a 5 pregões depois do dia da recomendação, usando fechamentos de `series_diarias`. Ativo ou Ibovespa sem fechamento no dia n: n é omitido, não preenchido com zero.
- Amostra e janela explícitas no rodapé, como em todo número do Consultor.

## Critérios de aceite
- [ ] A variação contra o Ibovespa dos pregões seguintes bate com a conta feita à mão sobre a série de fixture; sem pregão seguinte, o texto é "ainda sem resultado".
- [ ] O coletor `consultor_fechamento` grava o diário sem visita à página e não duplica quando a decisão é igual à do dia anterior.

## Invariantes de produção
- O diário tem uma linha por ativo avaliado para cada pregão dos últimos 5, sem depender de alguém ter aberto a página.

## Fora do escopo
- Janela maior que 5 pregões.
