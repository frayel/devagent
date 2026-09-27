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

## brapi.dev · limites do plano gratuito (verificado em 2026-09-27)

- 15.000 requisições por ciclo mensal e 1 requisição simultânea.
- `/api/quote/{tickers}` com vários ativos na mesma chamada não serve no gratuito; uma requisição por ativo estouraria a cota (30 ativos × ~40 coletas por dia).
- `/api/quote/list` não exige token e traz `stock`, `close`, `change` (% do dia), `volume` e `type` de todas as ações. As maiores altas e baixas usam uma única chamada: `?type=stock&sortBy=volume&sortOrder=desc&limit=100`, e o ranking sai das 100 ações mais negociadas do dia.
- Fonte: https://brapi.dev/docs/acoes/list e https://brapi.dev/faq/tem-algum-limite
