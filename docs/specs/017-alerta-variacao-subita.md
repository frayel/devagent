---
id: 017
titulo: Alerta de Variação Súbita (Flash Movements)
status: ready
esforco: M
---

## Problema
O investidor que olha o painel às 15h quer saber: algum papel disparou ou derreteu *agora*, ou as maiores altas/baixas do dia já estavam assim desde de manhã? Retorno diário esconde movimentos bruscos recentes.

## Comportamento esperado
Na tela inicial, um novo painel pequeno (abaixo de Radar Intraday ou Alertas de Volume) chamado "Variação Súbita". Ele exibe uma lista curta (máximo 3) de ações que tiveram variação expressiva (ex: > 1.5%) na última hora. Cada item mostra:
- Ticker.
- Movimento na última hora (ex: +2.1%).
- "Coletado em:" e "Fonte:" (yfinance).

Se nenhuma ação atender ao critério, exibe "Nenhum movimento brusco recente detectado."

## Fontes de dados
- **yfinance:** uso da API `history(period="1d", interval="15m")` ou similar para buscar fechamentos intraday recentes.
- Limitado às ações de maior liquidez (o mesmo universo de 30 ações de "Alertas de Volume").
- Plano B: degrada graciosamente e não exibe alertas.

## Cálculos
- Usa a lista das 30 ações principais e obtém o histórico intraday.
- Compara o preço mais recente (últimos 15 min) com o preço de 1 hora atrás (ex: 4 intervalos de 15m atrás).
- Calcula variação percentual.
- Filtra variações cujo valor absoluto é > 1.5%.
- Ordena por maior variação absoluta e pega o top 3.

## Critérios de aceite
- [ ] O banco de dados SQLite armazena o cache deste coletor (`variacao_subita_cache`).
- [ ] Quando pelo menos um papel tem variação na última hora > 1.5%, a lista mostra o papel e a %.
- [ ] Quando nenhum tem, exibe mensagem "Nenhum movimento brusco recente".
- [ ] Falha da fonte yfinance captura a exceção, o componente não quebra a página, apenas não exibe dado.

## Invariantes de produção
- A chave `variacao_subita` existe dentro de `paineis` no `/api/snapshot`.
- O valor possui `coletado_em`, `fonte` e uma lista `alertas`.

## Fora do escopo
- Disparo de notificações via email/push.
- Visualização gráfica de velas (candlesticks) destes 15 minutos.
