---
id: 022
titulo: Manchete Dinâmica
status: done
esforco: M
---

## Problema
A página do dashboard está ficando muito longa com o acúmulo de novos painéis, dificultando a rápida compreensão do clima do mercado para o usuário que acessa pelo celular. O usuário quer entender o sentimento geral do pregão em uma frase sem precisar rolar a página.

## Comportamento esperado
Uma seção textual curta no topo da página (acima dos painéis Macro/Micro) que sintetiza os principais indicadores de mercado já em cache (ex: direção do Ibovespa, termômetro de dispersão, apetite a risco). O texto muda dinamicamente com base em regras que combinam essas variáveis.

## Fontes de dados
Nenhuma nova fonte de dados será necessária. Utiliza os dados já cacheados pelos coletores existentes.

## Cálculos
Combinação lógica simples dos dados agregados. Exemplo: se Ibovespa está em alta, dispersão aponta maioria de altas e apetite a risco é positivo, a manchete pode ser "Dia de otimismo generalizado com forte tomada de risco".

## Critérios de aceite
- [ ] verificável por teste automatizado: a manchete é gerada corretamente com base em dados de fixtures locais simulando cenários variados.
- [ ] verificável visualmente (via capturas de tela): a manchete está visível no topo da página, tanto no desktop quanto no mobile, sem quebra de layout.

## Invariantes de produção
- A página renderiza uma frase resumida baseada nos indicadores principais.
- Nenhum acesso adicional de rede é realizado.

## Fora do escopo
Geração de textos complexos usando LLMs. Análise sentimental individual por ativo.
