# Changelog

## [Unreleased]
- feat: Implementa painéis de Maiores Altas e Maiores Baixas (Spec 002).
### Fixed
- test(highlights): Adiciona cobertura para os critérios da spec 002 marcados como sem teste: testa comportamento com menos de 5 ativos, testa a presença da fonte no template da página, e valida a ordenação do ranking de maiores altas e maiores baixas. Testes de maiores altas e baixas não levam mais 2 minutos após isolamento com monkeypatch.
- Maiores altas e baixas vazias com `BRAPI_TOKEN`: o plano gratuito da brapi não aceita 30 ativos numa chamada. O coletor passa a usar `/api/quote/list` (uma chamada, sem token), com ranking entre as 100 ações mais negociadas do dia; Yahoo continua como reserva.
- `httpx` faltava em `requirements.txt`: os coletores não rodariam em produção.
- fix(coleta): introduzido `fetch_with_retry` em `app/collectors/utils.py` com limite de requisições de 2s, User-Agent identificável e *backoff* exponencial de retry em erros 429 e 5xx, de acordo com as diretrizes do AGENTS.md seção 9. Substituídas chamadas diretas via `httpx` nos coletores.
- fix(coletor): Yahoo Finance fallback agora extrai a variação diária corretamente pelo penúltimo candle (ou `meta.previousClose`) em vez de basear o cálculo do candle do mês passado.
- CI: `ruff` fixado em 0.15.22; a versão 0.16 ampliou as regras padrão e deixou o lint vermelho na `main`, travando o auto-merge.
### Added
- Coleta automática dentro do web service (`app/agendador.py`, ADR 004): ao subir, a cada 15 min no pregão e a cada 2 h fora dele; diagnóstico em `/api/coleta`. Produção passa a exibir dados reais.
- `scripts/jules.py` e workflows `jules.yml`/`auditoria-llm.yml`: sessões do Jules criadas pela API sem aprovação de plano; planos pendentes aprovados e perguntas respondidas a cada 15 min.
- Auditor de produção (`auditoria/`): confere o site publicado contra Yahoo Finance/Stooq, calendário da B3, coerência dos números e vazamento de fixtures; workflow `auditoria-producao.yml` abre issues `producao-incorreta`.
- Persona do auditor LLM (`docs/agents/auditor.md`) e workflow `auditoria-achados.yml`, que transforma achados em issues.
- `automerge.yml` exige revisão humana para PRs que alteram o auditor.
- Feature: Ibovespa Hoje (MVP).
- Banco de dados SQLite local.
- Coletor de dados da brapi.dev e Yahoo Finance.
- Integração com Plotly.js para gráficos.
