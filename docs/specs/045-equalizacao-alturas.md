---
id: 045
titulo: Destaque Visual para a Maré
status: ready
esforco: P
---

## Problema
A Maré do Mercado é o principal indicador de clima, mas disputa muito a hierarquia visual. Consigo achar o que preciso, rápido? O layout do card da Maré do Mercado faz com que o gauge se sobreponha demais e exija mais atenção. Na `telas/desktop.png` os cards perdem clareza visual e têm disputas de alinhamento. A especificação não propõe mudar componentes, mas sim equalizar e melhorar o destaque no painel.

## Comportamento esperado
- O CSS do painel da Maré (`.painel-mare`) deverá usar ajustes de espaçamento.
- Diminuir o peso visual de outros elementos se houver necessidade para focar a visão do gauge da Maré, mas o escopo é principalmente de ajuste de CSS.
- Especificamente: o painel na interface deve ter maior respiro e coerência visual na grade principal (`visao-macro`).

## Fontes de dados
Nenhuma. Mudança de experiência (UI/CSS).

## Cálculos
Nenhum.

## Critérios de aceite
- [ ] verificáveis por teste automatizado (`test_design.py` passando)
- [ ] A tela reflete a melhoria proposta nas capturas, sem alterar a responsividade.

## Invariantes de produção
Sem alterações.

## Fora do escopo
Mudanças no backend, novos dados.
