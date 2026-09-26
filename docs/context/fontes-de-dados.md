# Contexto · Fontes de dados

Uma entrada por fonte. Atualize ao criar ou alterar coletor (skill `criar-coletor.md`).

## brapi.dev

- **Uso**: cotação e histórico do Ibovespa (`/api/quote/^BVSP`).
- **Autenticação**: `BRAPI_TOKEN` (variável de ambiente).
- **Limites**: plano gratuito tem cota de requisições; confira no site antes de aumentar a frequência.
- **Papel**: fonte principal. Se o token faltar, o coletor pula para a reserva.

## Yahoo Finance (endpoint de chart)

- **Uso**: reserva para cotação e histórico do Ibovespa.
- **Autenticação**: nenhuma.
- **Riscos**: API não oficial, sujeita a bloqueio e a mudanças de formato sem aviso. Não dependa dela como fonte única.
- **Pendência**: o coletor atual envia um User-Agent de navegador genérico; a seção 9 do `AGENTS.md` pede um User-Agent identificável do projeto.
