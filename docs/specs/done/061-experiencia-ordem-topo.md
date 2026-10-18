---
id: 061
titulo: Experiência - Ordem do Topo
status: done
esforco: P
gaveta: experiência
---

## Problema
A revisão de experiência nas capturas de tela revelou que os painéis "Clima Global" e "Motores do Índice" estão posicionados acima do painel "Ibovespa hoje". O guia visual (`PRODUTO.md`) especifica claramente que "Acima da dobra em 1440×900 ficam: o Ibovespa com gráfico (span-8), a Maré do mercado ao lado (span-4)". A posição atual empurra o protagonista principal da página para baixo da área prioritária.

## Comportamento esperado
- Os painéis "Clima Global" e "Motores do Índice" devem ser movidos para baixo da dupla "Ibovespa" e "Maré do mercado" no template (em HTML/Jinja).
- A linha 1 da grade deve ser exclusivamente "Ibovespa" e "Maré do mercado", restabelecendo o contato imediato do investidor com os números principais da B3.
- Nenhuma funcionalidade de coleta ou layout interno de cards deve ser removida; apenas a ordem no DOM será alterada.

## Fontes de dados
- Não se aplica (mudança apenas de layout HTML/CSS).
