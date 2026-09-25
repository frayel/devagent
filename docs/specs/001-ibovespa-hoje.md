---
id: 001
titulo: Ibovespa Hoje (MVP)
status: ready
esforco: P
---

## Problema
O investidor precisa saber rapidamente como o mercado (Ibovespa) fechou ou está operando no dia de hoje, e qual é a tendência recente, para balizar suas decisões.

## Comportamento esperado
Na página inicial (index), exibir:
- O último valor em pontos do Ibovespa.
- A variação do dia (em pontos e em percentual, com cor verde/vermelha dependendo do sinal).
- O horário exato da última coleta dos dados.
- Um gráfico de linha simples mostrando o fechamento dos últimos 30 pregões.

## Fontes de dados
- **URL**: brapi.dev (endpoint de tickers) ou yfinance (`^BVSP`).
- **Formato**: JSON (brapi) ou DataFrame (yfinance).
- **Frequência**: A cada 15 minutos (via cron).
- **Limites**: brapi tem limite de requisições no plano grátis; yfinance pode ter rate limit do Yahoo Finance.
- **Plano B**: Se brapi falhar, usar yfinance, e vice-versa.

## Cálculos
- Variação = `valor_atual - fechamento_anterior`.
- Variação % = `(variação / fechamento_anterior) * 100`.
- Gráfico: Pegar o array de `close` dos últimos 30 dias úteis.

## Critérios de aceite
- [ ] O endpoint `/` exibe as informações requeridas.
- [ ] A coleta dos dados é mockada e verificável em teste automatizado sem acesso à internet.
- [ ] O html base tem o aviso: "Conteúdo informativo gerado automaticamente. Não constitui recomendação de investimento." no rodapé.
- [ ] Falhas na API levam a exibição de mensagem de erro amigável sem derrubar a aplicação.

## Fora do escopo
- Dados em tempo real (streaming via websocket).
- Outros índices além do Ibovespa.
