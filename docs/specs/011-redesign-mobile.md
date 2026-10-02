---
id: 011
titulo: Revisão de Experiência (Foco Mobile)
status: ready
esforco: P
---

## Problema
A página no celular (390px) apresenta uma rolagem horizontal indesejada e uma falha na montagem da tabela no painel "Sensibilidade ao dólar", fazendo com que o `make telas` falhe com erro `PROBLEMA: rolagem horizontal de 80px em celular (390px)`. Além disso, a página está longa devido à introdução de vários painéis novos (Escudo contra Quedas, Força Relativa, Sensibilidade ao dólar, Radar de volume), todos empilhados na ordem de criação.

## Comportamento esperado
1. Eliminar a rolagem horizontal em telas de celular (390px). O principal suspeito é o painel "Sensibilidade ao dólar", que utiliza a classe `.duas` (grid com 1fr 1fr), apertando duas tabelas lado a lado em 390px.
2. Garantir que as tabelas do painel "Sensibilidade ao dólar" se empilhem em telas menores (celular), em vez de ficarem lado a lado.
3. Reorganizar a ordem dos painéis na home para que tenham agrupamento lógico.

## Fontes de dados
Nenhuma nova. Apenas ajustes em HTML/CSS.

## Cálculos
Nenhum novo.

## Critérios de aceite
- [ ] A classe `.duas` muda de comportamento em dispositivos móveis, empilhando seus itens (1 coluna) em telas menores que 768px.
- [ ] O script `make telas` não falha acusando rolagem horizontal.
- [ ] O layout e os painéis são exibidos na ordem lógica proposta.

## Invariantes de produção
N/A
