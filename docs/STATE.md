# Estado do Sistema

> **Coleta em produção (2026-09-27):** até esta data nenhuma coleta rodava em produção; o painel exibia "Dados não disponíveis". A coleta agora roda no próprio web service (`app/agendador.py`, ADR 004). Diagnóstico: `GET /api/coleta`.

## Implementado
- Núcleo do agente separado do produto (ADR 005 em `devagent/decisoes/`): processo em `devagent/`, produto em `PRODUTO.md`, contrato no `Makefile` e no `devagent.toml`.
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
- Spec 003 (Médias Móveis de 21 e 200 dias para o Ibovespa):
  - Inclusão dos campos `mm21` e `mm200` no cache `ibovespa_cache`.
  - Cálculo de médias móveis baseado em histórico estendido (`1y`).
  - Card "Tendência (Ibovespa)" com sinais de alta, baixa ou neutra.
  - Atualização automática em cada coleta com fallback para dados insuficientes.
- Spec 004 (Sentimento de Mercado Baseado na Dispersão):
  - Termômetro de dispersão na página inicial com contagem de altas/baixas e proporção.
  - Banco de dados SQLite (`highlights_cache`) armazena as contagens.
  - Exposição no JSON `/api/snapshot`.
- Spec 005 (Alertas de Volume Anormal):
  - Banco de dados SQLite (`volume_alert_cache`).
  - Coletor buscando volume das 30 ações mais líquidas via `yfinance` (spark endpoint).
  - Cálculo de anomalia (volume atual > 50% da média das últimas 3 semanas).
  - Exibição de tabela de alertas na home e via contrato `/api/snapshot`.
