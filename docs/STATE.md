# Estado do Sistema

> **Coleta em produção (2026-09-27):** até esta data nenhuma coleta rodava em produção; o painel exibia "Dados não disponíveis". A coleta agora roda no próprio web service (`app/agendador.py`, ADR 004). Diagnóstico: `GET /api/coleta`.

## Experiência

- Última revisão de experiência: 02/10/2026 (Redesign 008)
- Painéis, seções ou telas acrescentados desde a última revisão: 0 (com 3, o Passo 7 faz uma revisão de experiência; veja `devagent/CICLO.md`).

## Implementado
- Spec 012 (Índice de Coesão):
  - Banco de dados SQLite (`coesao_cache`).
  - Coletor com `yfinance` para as 10 principais ações e o Ibovespa, calculando convergência de direção.
  - Adicionado ao contrato `/api/snapshot`.
- Spec 011 (Revisão de Experiência Mobile):
  - Correção de rolagem horizontal em telas de 390px (ajuste `.duas`).
  - Reorganização lógica dos painéis da página inicial em `index.html`.
- Spec 009 (Força Relativa):
  - Banco de dados SQLite (`forca_relativa_cache`).
  - Coletor com yfinance buscando variações e comparando com benchmark IBOV.
  - Exibição das ações com maior e menor força relativa em 30 pregões.
  - Adicionado ao contrato `/api/snapshot`.

- Spec 007 (Fator Mola):
  - Banco de dados SQLite (`fator_mola_cache`).
  - Coletor buscando volume das ações mais líquidas via `yfinance` e `brapi`.
  - Exibição de ações com maior recuperação no intraday em relação à mínima.
  - Adicionado ao contrato `/api/snapshot`.
- Spec 007 (Fator Mola):
  - Banco de dados SQLite (`fator_mola_cache`).
  - Coletor buscando volume das ações mais líquidas via `yfinance` e `brapi`.
  - Exibição de ações com maior recuperação no intraday em relação à mínima.
  - Adicionado ao contrato `/api/snapshot`.
- Spec 006 (Sensibilidade ao Dólar):
  - Banco de dados SQLite (`dolar_correlation_cache`).
  - Coletor com fonte de dados yfinance para BRL=X e 30 ações de alta liquidez.
  - Cálculo de correlação de Pearson sobre os retornos dos últimos 30 pregões sobrepostos.
  - Exibição de tabela de maiores correlações positivas e negativas.
  - Adicionado ao contrato `/api/snapshot`.
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

- Spec 010 (Escudo contra Quedas):
  - Banco de dados SQLite (`escudo_quedas_cache`).
  - Coletor buscando histórico do Ibovespa e ativos via `yfinance`.
  - Exibição do top 3 ativos que mais tiveram retornos positivos nos pregões de queda do Ibovespa nos últimos 30 pregões.
  - Adicionado ao contrato `/api/snapshot`.
