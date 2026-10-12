---
id: 047
titulo: Concentração de Força Vendedora
status: done
esforco: P
---

## Problema
O investidor precisa saber se uma queda do Ibovespa reflete pânico generalizado ou se está concentrada no derretimento de poucos ativos específicos (ex: Petrobras ou Vale afundando o índice sozinhas).

## Comportamento esperado
Um novo painel "Pressão Vendedora" na seção de visão macro.
O painel exibe a contribuição somada dos 5 ativos com o pior desempenho absoluto (em termos de impacto no índice, ou seja, variação ponderada) no dia atual, em formato percentual e com texto explicativo. Ex: "Os 5 piores ativos hoje respondem por 65% da queda total do Ibovespa".
Se o índice estiver no positivo, o painel não precisa ser exibido ou pode indicar "Sem pressão dominante".

## Fontes de dados
`yfinance` (cotação intraday para ^BVSP e os ativos que compõem o índice, focado nos pesos principais).

## Cálculos
- Similar à Concentração de Ganhos / Peso Pesado, mas focado nas maiores contribuições negativas.
- Calcular a variação do Ibovespa.
- Se a variação do Ibovespa for negativa:
  - Ordenar os ativos pela sua contribuição individual (variação * peso) de forma crescente (os mais negativos primeiro).
  - Somar a contribuição dos 5 mais negativos.
  - Dividir essa soma pela variação total do índice para obter o percentual de concentração.

## Critérios de aceite
- [x] A lógica de cálculo possui cobertura de testes garantindo matemática correta (positiva, negativa e neutra).
- [x] Os dados refletem em um novo campo `concentracao_vendedora` em `/api/snapshot`.
- [x] O painel aparece condicionalmente apenas quando a contribuição é relevante e o IBOV está negativo.

## Invariantes de produção
- A consulta à API e atualização do banco ocorre no ciclo do agendador e lida com indisponibilidades.
- O campo em `/api/snapshot` não quebra o schema do JSON existente.
