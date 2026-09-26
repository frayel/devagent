# Contexto · Domínio B3

Fatos de mercado que afetam specs e cálculos. Confirme horários e feriados no calendário oficial da B3, que muda com o tempo.

- **Ibovespa**: principal índice da B3. Ticker `^BVSP` no Yahoo Finance e na brapi.
- **Ações**: tickers com sufixo numérico (`PETR4`, `VALE3`); no Yahoo levam `.SA` (`PETR4.SA`).
- **Pregão**: sessão regular durante a tarde no horário de Brasília (UTC−3, sem horário de verão). Fora do pregão, o "último valor" é o fechamento anterior.
- **Feriados**: a bolsa fecha em feriados nacionais e em algumas datas próprias. "Últimos 30 pregões" não é "últimos 30 dias".
- **Atraso**: fontes gratuitas costumam ter atraso de ~15 minutos. Exiba o atraso quando a fonte informar.
- **Proventos**: dividendos e desdobramentos distorcem séries de preço. Para retornos históricos, use preços ajustados e diga isso na tela.
- **Variação do dia**: `último − fechamento anterior`, e o percentual sobre o fechamento anterior.
- **Honestidade estatística**: com poucos eventos parecidos no histórico, uma "probabilidade" não significa nada. Mostre sempre o tamanho da amostra.
