---
id: 002
titulo: Maiores Altas e Baixas do Dia
status: done
esforco: P
---

## Problema
O investidor quer saber rapidamente quais papéis mais se destacaram positiva e negativamente no dia (ou até o momento, se o pregão estiver aberto) para identificar oportunidades, ruídos ou reações a notícias.

## Comportamento esperado
Na página inicial, abaixo do Ibovespa Hoje, exibir duas pequenas tabelas:
- **Maiores Altas**: Top 5 ações com maior variação percentual positiva.
- **Maiores Baixas**: Top 5 ações com maior variação percentual negativa.

Cada tabela deve conter:
- Ticker da ação (ex: PETR4).
- Preço atual.
- Variação percentual diária (com cor verde ou vermelha).
- A fonte dos dados e o horário da última coleta.

## Fontes de dados
- **URL**: brapi.dev endpoint de quote com uma lista fixa de tickers (ex: composição do Ibovespa) ou algum endpoint específico se existir.
- **Formato**: JSON.
- **Frequência**: A cada 15 minutos (via cron).
- **Limites**: Plano grátis da brapi.
- **Plano B**: Fazer fallback para a yfinance e pegar a cotação de uma cesta dos tickers mais líquidos da B3.

## Cálculos
- Obter a lista de ações (ex: componentes do Ibovespa ou tickers mais líquidos).
- Filtrar os ativos válidos e ordenar pela variação percentual (`regularMarketChangePercent`).
- Pegar os 5 primeiros da lista em ordem decrescente (Maiores Altas) e os 5 últimos (ou 5 primeiros da lista em ordem crescente) para Maiores Baixas.
- Salvar no banco (SQLite) para leitura na view.

## Critérios de aceite
- [ ] O banco de dados armazena o cache do ranking de altas e baixas.
- [ ] A view renderiza as duas tabelas corretamente.
- [ ] A coleta dos dados é mockada via respx em testes automatizados.
- [ ] O painel não quebra se a fonte retornar menos que 5 ativos.
- [ ] A fonte e hora da coleta são explicitadas na tela.

## Fora do escopo
- Ações com baixa liquidez (microcaps, penny stocks) que distorçam as variações.
- Ranking de volume negociado.
