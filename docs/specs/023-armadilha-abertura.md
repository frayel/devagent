---
id: 023
titulo: Armadilha de Abertura (Gap Trap)
status: ready
esforco: M
---

## Problema
Muitos investidores de varejo compram ações assim que a bolsa abre, atraídos por uma abertura em forte alta (gap). Muitas vezes, isso é uma armadilha ("gap trap"), onde grandes players usam a liquidez da abertura para vender, fazendo a ação derreter ao longo do dia. O investidor quer saber: "quais ações abriram eufóricas, mas já reverteram violentamente para baixo, prendendo compradores?"

## Comportamento esperado
O painel "Armadilhas de Abertura" aparece na visão micro. Ele exibe uma lista (máximo 3) com as ações que cumprem as condições:
1. O preço de abertura de hoje foi pelo menos 1% superior à máxima do pregão de ontem (Gap de alta).
2. O preço atual agora é menor que o fechamento de ontem (Reversão completa do gap).

Para cada ação na lista, o painel exibe o ticker, o preço atual, e uma tag visual (ex: "Gap Trap") alertando a reversão.
Se não houver ações nesta condição, o painel exibe: "Nenhuma armadilha detectada hoje".

## Fontes de dados
yfinance. Coleta a cada 15 minutos do endpoint de histórico diário com período de 2 dias (`period=2d`). Se yfinance falhar, o painel exibe "Dados não disponíveis".

## Cálculos
1. Para um conjunto das 30 ações mais líquidas.
2. Gap de Abertura: `(Open_hoje - High_ontem) / High_ontem > 0.01` (1%).
3. Reversão: `Preço_atual < Close_ontem`.

## Critérios de aceite
- [ ] Função no service capaz de identificar o padrão Gap Trap com base num mock de preços.
- [ ] Painel não quebra a página se não houver dados, exibindo estado vazio correto.
- [ ] O componente exibe a formatação correta para as ações retornadas pelo banco/cache.
- [ ] O endpoint `/api/snapshot` inclui as informações deste novo painel.

## Invariantes de produção
- O painel exibe apenas papéis cujo preço atual é efetivamente menor que o de fechamento anterior.
- Se o painel não exibir nada, não deve haver erro no console.

## Fora do escopo
- Análise tick-a-tick de toda a B3 (limitado a um basket de alta liquidez).
- Acionamento de notificações por e-mail ou push.
