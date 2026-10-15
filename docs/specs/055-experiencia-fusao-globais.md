---
id: 055
titulo: Experiência: Fusão de Indicadores Globais
status: done
esforco: P
---

## Problema
O Clima Global e os Motores do Índice estão ocupando muito espaço na primeira dobra de "Visão Geral", empurrando o gráfico do Ibovespa e a Maré para baixo. A informação precisa ser mais condensada.

## Comportamento esperado
Reorganizar a seção "Visão Geral" no `index.html`.
Unir o "Clima Global" e os "Motores do Índice" (se renderizados separadamente) ou ajustar suas classes de grid de modo que eles ocupem a mesma linha superior de forma mais compacta (por exemplo, transformando blocos largos em blocos mais estreitos de span menores, se possível). A ideia é liberar espaço vital. Como a Maré e o Ibovespa são cruciais, essa reorganização visual visa manter a densidade informacional sem perder a clareza, possivelmente agrupando-os no layout.
Dado o guia visual, podemos consolidá-los colocando o painel `clima_global` e `motores_indice` num contêiner unificado, ou redefinindo suas larguras CSS, reduzindo a altura do cabeçalho de cada um.
Para este MVP da ideia, vamos colocá-los lado a lado reduzindo o `span` do "Clima Global" e "Motores do Índice" na home, para que se encaixem melhor na primeira dobra.

## Fontes de dados
Nenhuma nova fonte. Reorganização visual/CSS da view no `app/templates/index.html`.

## Cálculos
Sem novos cálculos.

## Critérios de aceite
- [ ] O layout de `index.html` ajusta as classes de grid (`span-X`) para "Clima Global" e "Motores do Índice" para que fiquem mais harmoniosos na primeira linha da Visão Geral.
- [ ] As telas geradas (`make telas`) refletem um layout mais compacto ou balanceado sem quebrar em resoluções menores.

## Invariantes de produção
- A página continua rendendo 200 OK e passa nos testes do `make audit`.
- `/api/snapshot` não sofre alteração.

## Fora do escopo
Novas métricas no clima global ou nos motores do índice.
