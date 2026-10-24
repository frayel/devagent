---
id: 2026-10-24-painel-correlacao-di-ausente
severidade: media
painel: correlacao_di
status: aberto
visto_em: 2026-10-24T00:00:00-03:00
pr: 445
---

# PR fechou a spec sem implementar o painel

## O que acontece
O PR 445 (título `feat: painel de correlação Ibovespa e DI (#445)`) foi mesclado fechando a Spec 081, mas a string `correlacao_di` não foi encontrada em lugar nenhum do código sob o diretório `app/`. O endpoint `/api/snapshot` não exibe a chave `correlacao_di` no JSON. O painel não existe na página inicial.

## O que deveria acontecer
De acordo com os Critérios de Aceite e Invariantes da Spec 081:
- "A chave do painel correlacao_di deve existir no /api/snapshot."
- "O painel é renderizado na tela e ocultado adequadamente quando os dados estiverem indisponíveis."
O comportamento prometido não foi cumprido.

## Evidência
Comando `grep -rn "correlacao_di" app/` retorna vazio.
O endpoint `/api/snapshot` não contém `correlacao_di` dentro de `paineis`.

## Como reproduzir
1. Rode `grep -rn "correlacao_di" app/`
2. Inicie a aplicação com `make start` e acesse `/api/snapshot`.
