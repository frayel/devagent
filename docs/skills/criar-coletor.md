# Skill · Criar um coletor de dados

Use ao implementar uma spec que traga uma fonte nova.

## Antes do código

1. Registre a fonte em `docs/context/fontes-de-dados.md`: URL, formato, autenticação, limites, termos de uso, `robots.txt`, atraso dos dados e fonte reserva.
2. Se a fonte proíbe coleta automatizada, pare e escolha outra (seção 9 do `AGENTS.md`).

## Estrutura

- Um módulo por fonte em `app/collectors/`, com uma função pública que devolve um objeto tipado ou `None`.
- `httpx` com `timeout` explícito, retry com backoff (no máximo 3 tentativas) e `User-Agent` identificável do projeto.
- No máximo 1 requisição a cada 2 segundos por domínio.
- O coletor grava no banco; a página só lê do banco. Nunca colete durante uma requisição do usuário.
- Toda linha gravada carrega `fonte` e `coletado_em` (UTC).
- Ponto de entrada executável (`python -m app.collectors.<nome>`) para o Cron Job do Render.

## Testes

- Salve uma resposta real em `tests/fixtures/<fonte>-<caso>.json` (ou `.html`).
- Mocke o HTTP com `respx`. Os testes nunca acessam a internet.
- Cubra: resposta válida, resposta vazia ou malformada, erro HTTP, timeout, e o fallback para a fonte reserva.

## Produção

- Qualquer biblioteca usada pelo coletor vai para `requirements.txt`.
- Declare o Cron Job no `render.yaml` e documente em `docs/context/operacao.md`.
