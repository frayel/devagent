# Contexto · Operação deste produto

O fluxo de entrega, os workflows e os secrets do núcleo estão em `devagent/OPERACAO.md`. Aqui ficam só as particularidades do Painel B3.

- **URL de produção:** `producao_url` em `devagent.toml` (hoje `https://devagent-vb52.onrender.com`).
- **Coleta:** roda dentro do web service (`app/agendador.py`, ADR 004); `GET /api/coleta` mostra a última rodada e o último erro. `COLETA_AUTOMATICA=0` desliga.
- **Banco:** PostgreSQL (Neon) configurado via `DATABASE_URL` (ADRs 006 e 007) para manter persistência através de hibernações do Render. Sem `DATABASE_URL`, a aplicação usa o SQLite efêmero para dev/teste local.
- **Horários da auditoria:** amarrados ao pregão da B3 nos crons de `auditoria-producao.yml` e `auditoria-llm.yml` (detalhes na seção 9 do `PRODUTO.md`).
- **Variáveis do produto:** seção 10 do `PRODUTO.md`.
