# Changelog

## [Unreleased]
- feat: Implementa painéis de Maiores Altas e Maiores Baixas (Spec 002).
### Fixed
- CI: `ruff` fixado em 0.15.22; a versão 0.16 ampliou as regras padrão e deixou o lint vermelho na `main`, travando o auto-merge.
### Added
- `scripts/jules.py` e workflows `jules.yml`/`auditoria-llm.yml`: sessões do Jules criadas pela API sem aprovação de plano; planos pendentes aprovados e perguntas respondidas a cada 15 min.
- Auditor de produção (`auditoria/`): confere o site publicado contra Yahoo Finance/Stooq, calendário da B3, coerência dos números e vazamento de fixtures; workflow `auditoria-producao.yml` abre issues `producao-incorreta`.
- Persona do auditor LLM (`docs/agents/auditor.md`) e workflow `auditoria-achados.yml`, que transforma achados em issues.
- `automerge.yml` exige revisão humana para PRs que alteram o auditor.
- Feature: Ibovespa Hoje (MVP).
- Banco de dados SQLite local.
- Coletor de dados da brapi.dev e Yahoo Finance.
- Integração com Plotly.js para gráficos.
