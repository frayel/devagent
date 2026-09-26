# Estado do Sistema

## Implementado
- Configuração inicial do projeto (FastAPI, Ruff, Mypy, Pytest).
- Spec 001 (Ibovespa Hoje):
  - Banco de dados SQLite (`ibovespa_cache`).
  - Coletor com duas fontes: brapi.dev e fallback para Yahoo Finance.
  - Exibição de pontuação, variação diária e horário de coleta.
  - Gráfico de linha dos últimos 30 pregões usando Plotly.js.
  - Tratamento de falhas nas fontes de dados.
- Spec 002 (Maiores Altas e Baixas do Dia):
  - Banco de dados SQLite para cache (`altas_baixas_cache`).
  - Coletor com duas fontes: brapi.dev e fallback para Yahoo Finance com tickers líquidos da B3.
  - Exibição de duas tabelas (altas e baixas) com ticker, preço e variação percentual.
  - Tratamento de formatação (cores verde/vermelho).
