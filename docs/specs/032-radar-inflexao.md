---
id: 032
titulo: Radar de Inflexão (Reversão de Tendência)
status: done
esforco: M
---

## Problema
O usuário quer saber quais ações que estavam caindo nos últimos dias ou semanas finalmente começaram a subir com força (reversão de tendência).

## Comportamento esperado
Um novo painel "Inflexão de Tendência" na seção "Rankings & Destaques".
Exibe uma tabela com até 5 ações que apresentaram queda cumulativa nos últimos 15 dias, mas que hoje apresentam alta > 2%.
A tabela exibe o ticker da ação e sua variação no dia atual.

## Fontes de dados
`yfinance` (endpoint spark para cotações diárias dos últimos 15 dias).
Plano B: fallback seguro ignorando ativos em caso de timeout.

## Cálculos
- Baixar histórico de 15 dias úteis.
- Para cada ação, calcular o retorno acumulado de D-15 a D-1.
- Filtrar ações com retorno acumulado (D-15 a D-1) < -5%.
- Filtrar aquelas que hoje (D0) têm variação > +2%.
- Ordenar pelas que tiveram maior queda acumulada e agora revertem.

## Critérios de aceite
- [x] verificáveis por teste automatizado simulando retornos simulados.
- [x] O painel aparece no snapshot com até 5 ativos e suas variações diárias.

## Invariantes de produção
A chave `radar_inflexao` em `/api/snapshot` retorna uma lista válida de ações em formato JSON conforme as outras métricas.

## Fora do escopo
Não mostraremos gráficos sparklines neste painel, apenas os nomes e a porcentagem.
