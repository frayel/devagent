# Spec 059: Termômetro de Exaustão de Tendência

status: ready

## 1. O Problema
No final de ciclos de alta de curto prazo, o mercado frequentemente exibe um padrão onde o preço continua a subir, mas o interesse institucional (volume) diminui ("subindo sem força"). Identificar quais ativos de alta liquidez estão nesse estado ajuda o investidor a antecipar reversões de tendência (bull traps ou topos locais) antes que o preço comece a cair.

## 2. A Solução
Adicionar um painel "Exaustão de Tendência" na seção "Alertas Intraday". Ele varre a cesta de liquidez buscando ativos que cumpram duas condições simultâneas no fechamento diário recente:
1. Preço de fechamento em alta por pelo menos 3 pregões consecutivos.
2. Volume financeiro em queda por pelo menos 3 pregões consecutivos.

## 3. Como o usuário usa
O investidor que possui uma das ações listadas na carteira é alertado de que a alta atual carece de suporte de volume, podendo decidir realizar lucros ou ajustar o stop loss.

## 4. O que não faz parte (Out of scope)
- Gráficos de volume intraday.
- Sinais de exaustão de tendência de baixa (quedas consecutivas com volume decrescente).
- Outros indicadores de momentum (como RSI, MACD). Apenas preço puro e volume.

## 5. Casos de Teste (Critérios de Aceite)
- O coletor retorna com sucesso ativos que sobem há 3 ou mais dias com volumes decrescentes.
- O painel exibe "Dias Consecutivos" e a variação acumulada do período para os ativos identificados.
- O cache (`exaustao_tendencia_cache`) atualiza a tabela SQLite no formato do projeto.
- O endpoint `/api/snapshot` reflete a chave `exaustao_tendencia`.

## 6. Invariantes de produção
- A consulta é feita usando a API do Yahoo Finance (`spark`), com cache adequado e timeouts aplicados.
- A exclusão de fundos imobiliários/índices se mantém (apenas cesta primária de liquidez e ações válidas).
