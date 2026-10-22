# Contexto · Operação deste produto

O fluxo de entrega, os workflows e os secrets do núcleo estão em `devagent/OPERACAO.md`. Aqui ficam só as particularidades do Painel B3.

- **URL de produção:** `producao_url` em `devagent.toml` (hoje `https://devagent-vb52.onrender.com`).
- **Coleta:** roda dentro do web service (`app/agendador.py`, ADR 004); `GET /api/coleta` mostra a última rodada e o último erro. `COLETA_AUTOMATICA=0` desliga.
- **Banco:** Postgres (Neon) via `DATABASE_URL` para persistência entre hibernações. O SQLite só é usado se `DATABASE_URL` não estiver definido (desenvolvimento local e testes).
- **Horários da auditoria:** amarrados ao pregão da B3 nos crons de `auditoria-producao.yml` e `auditoria-llm.yml` (detalhes na seção 9 do `PRODUTO.md`).
- **Variáveis do produto:** seção 10 do `PRODUTO.md`.
