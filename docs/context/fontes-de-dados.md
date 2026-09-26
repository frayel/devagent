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
- **Armadilhas**: Ao utilizar `range=1mo` no endpoint de chart, o campo `meta.chartPreviousClose` aponta para o fechamento anterior ao primeiro candle (ou seja, de cerca de um mês atrás), e não para o último fechamento do dia útil anterior. Para calcular a variação diária, deve-se extrair o penúltimo `close` da série, e utilizar os dados do `meta` como fallback secundário.
- **Pendência**: o coletor atual envia um User-Agent de navegador genérico; a seção 9 do `AGENTS.md` pede um User-Agent identificável do projeto.
