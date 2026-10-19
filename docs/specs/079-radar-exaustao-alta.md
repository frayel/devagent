---
id: 079
titulo: Capacidade Nova: Radar de Exaustão de Alta
status: ready
esforco: M
gaveta: capacidade nova
---

## Problema
O usuário deseja saber quais ativos estão perdendo força de compra após um rali no intraday, sinalizando possível reversão para baixa.

## Comportamento esperado
Um novo painel na seção "Alertas Intraday" que exibe uma tabela com os ativos (tickers) que subiram mais de 2% no dia, mas cuja sombra superior do candle diário atual é pelo menos o dobro do corpo do candle (indicando forte rejeição nos topos).

## Fontes de dados
yfinance (intraday via endpoint spark ou chart de 1d). Plano B: ignorar o painel caso a API falhe, não quebrando o carregamento.

## Cálculos
Para os ativos monitorados (cesta B3):
1. Calcular variação diária: (Fechamento atual / Abertura) - 1.
2. Identificar se variação >= 2%.
3. Calcular corpo: abs(Fechamento - Abertura).
4. Calcular sombra superior: Máxima - max(Abertura, Fechamento).
5. Filtrar ativos onde sombra superior >= 2 * corpo.

## Critérios de aceite
- [ ] O coletor salva corretamente os ativos em rejeição no cache SQLite.
- [ ] O painel exibe "Nenhum ativo em exaustão" quando a lista é vazia.
- [ ] O componente visual segue o guia docs/DESIGN.md e usa as cores padrão de alerta.

## Invariantes de produção
- A chave exaustao_alta deve estar presente no /api/snapshot e retornar uma lista (mesmo que vazia) de dicionários com chaves ticker e variacao.

## Fora do escopo
Alertas em tempo real via push ou e-mail. Funciona apenas no carregamento da tela/painel.
