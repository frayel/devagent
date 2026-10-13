---
id: 049
titulo: Revisão de Experiência - Consolidação de Gauges na Maré do Mercado
status: done
esforco: P
---

## Problema
A tela atual apresenta vários indicadores de "gauge" (medidores semicirculares) espalhados, como Apetite a Risco e Rotação de Capital, o que dificulta a leitura rápida da saúde geral do mercado. Consolidar esses medidores num único painel central ("Maré do Mercado") simplificará a visualização e limpará a interface. A pergunta que responde é: "Como simplificar a leitura de medidores espalhados?"

## Comportamento esperado
- Os medidores (gauges) de "Apetite a Risco" e "Rotação de Capital" devem ser movidos/integrados visualmente no mesmo agrupamento ou painel da "Maré do Mercado".
- Os painéis independentes originais de Apetite a Risco e Rotação de Capital devem ser removidos ou mesclados para não poluir a tela.
- A visualização na grade principal deve ficar mais limpa, mantendo a funcionalidade dos medidores dentro de um contexto unificado (Maré do Mercado).

## Fontes de dados
- Os dados já são fornecidos pelas implementações existentes de `apetite_risco_cache`, `rotacao_capital_cache` e `mare_cache`. Não há necessidade de novas fontes.

## Critérios de aceite
1. O painel "Maré do Mercado" (`.painel-mare`) na renderização do `index.html` deve conter ou agrupar os indicadores de Apetite a Risco e Rotação de Capital.
2. A tela inicial (`index.html`) não deve mais exibir painéis isolados separados para "Apetite a Risco" e "Rotação de Capital" fora do contexto da Maré.
3. Os testes visuais (`make telas`) devem renderizar corretamente sem quebra de layout, demonstrando a consolidação.
4. O contrato `/api/snapshot` não precisa sofrer alterações na estrutura dos dados retornados, a menos que os painéis sejam removidos da API (o que não é o caso, apenas a apresentação visual está sendo alterada).

## Fora do escopo
- Alterações na lógica de cálculo (backend) do Apetite a Risco, Rotação de Capital ou Maré do Mercado.
- Inserção de novos gauges não relacionados a esses três conceitos.
