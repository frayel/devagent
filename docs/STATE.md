# Estado do Sistema

> **Coleta em produção (2026-09-27):** até esta data nenhuma coleta rodava em produção; o painel exibia "Dados não disponíveis". A coleta agora roda no próprio web service (`app/agendador.py`, ADR 004). Diagnóstico: `GET /api/coleta`.

## Implementado
- Configuração inicial do projeto (FastAPI, Ruff, Mypy, Pytest).
- Spec 001 (Ibovespa Hoje):
  - Banco de dados SQLite (`ibovespa_cache`).
  - Coletor com duas fontes: brapi.dev e fallback para Yahoo Finance.
  - Exibição de pontuação, variação diária e horário de coleta.
  - Gráfico de linha dos últimos 30 pregões usando Plotly.js.
  - Tratamento de falhas nas fontes de dados.
- Spec 002 (Maiores Altas e Baixas do Dia):
  - Banco de dados SQLite (`highlights_cache`).
  - Coletor com fonte de dados brapi.dev e fallback yfinance, rastreando lista de 30 tickers de alta liquidez.
  - Exibição de duas tabelas com top 5 altas e baixas (variação percentual).
  - Tratamento de falhas e UI para dados não disponíveis.
