---
id: 052
titulo: Termômetro de Clima Externo
status: done
esforco: M
---

## Problema
O investidor, às 10h05 (abertura), não sabe se um forte gap de alta ou baixa do Ibovespa é motivado por fatores locais ou se o mercado está apenas acompanhando o humor global (EUA). A página precisa mostrar se o "clima lá fora" está calmo, tenso, ou em euforia, para contextualizar o movimento da B3.

## Comportamento esperado
Será adicionado um novo painel pequeno (Span 2 ou 3) na Visão Geral, logo acima ou ao lado dos motores do índice.
O painel exibirá o texto "Clima Global", com um indicador de cor (Verde, Amarelo, Vermelho, Cinza) e uma palavra-chave: "Apetite a Risco", "Cautela", "Aversão a Risco" ou "Neutro", baseado no cruzamento do S&P 500 Futuros e VIX.
Também mostrará os valores percentuais dos dois indicadores menores na base do painel.

## Fontes de dados
Yahoo Finance (endpoints diários e/ou chart intraday, usando os tickers `ES=F` para S&P Futuros e `^VIX` para o VIX).
Plano B: Se uma das consultas falhar, exibir "Clima: Indisponível".

## Cálculos
O clima é "Aversão a Risco" se o VIX > +3% e ES=F < -0.5%.
O clima é "Apetite a Risco" se o VIX < -2% e ES=F > +0.5%.
Do contrário, "Neutro".

## Critérios de aceite
- [ ] O endpoint de mock HTTP valida que a resposta extrai corretamente o `ES=F` e `^VIX`.
- [ ] A chave `clima_global` com o status textual e as métricas está presente na rota `api/snapshot`.
- [ ] A interface exibe a classe de cor correta baseada no humor global.

## Invariantes de produção
- A chave `clima_global` deve existir e conter valores plausíveis de S&P e VIX (VIX sempre positivo).

## Fora do escopo
- Acompanhar mercados europeus ou asiáticos, DXY, commodities. Foco apenas na dupla S&P Futuro e VIX.
