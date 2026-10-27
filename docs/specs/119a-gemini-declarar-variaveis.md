---
id: 119a
titulo: Declarar as variáveis no render
status: draft
esforco: P
gaveta: saúde técnica
aceite: tests/test_aceite_119a.py
revisada: 2026-10-27
---

## Problema

Como as demais variáveis além do MT5 são rastreadas no repositório?

`render.yaml` declara só `MT5_API_URL` e `MT5_API_KEY` com `sync: false`. As demais variáveis (`GEMINI_API_KEY`, `GEMINI_MODELO`, `GEMINI_MAX_CHAMADAS_DIA`, `BRAPI_TOKEN`, `DATABASE_URL`) existem só no painel do Render, sem rastro no repositório.

## Comportamento esperado

### Variáveis declaradas

`render.yaml` passa a declarar, com `sync: false` e sem valores, `GEMINI_API_KEY`, `BRAPI_TOKEN` e `DATABASE_URL`, no mesmo padrão das variáveis do MT5, e o `PRODUTO.md` (tabela de variáveis) cita a validação periódica da chave. O adaptador `devagent/adaptadores/render_blueprint.py` e seus testes continuam verdes.

## Fontes de dados

Não aplicável.

## Critérios de aceite

- [ ] `render.yaml` declara as três variáveis com `sync: false`, sem valor, e os testes do adaptador do Render passam.
- [ ] O `PRODUTO.md` está atualizado.

## Invariantes de produção

- `render.yaml` mantém declaração sem valor das variáveis de ambiente de chaves.

## Fora do escopo

- Validação da chave no agendador.
- Alterar a interface do `/sistema`.

## Revisão

A spec foi marcada como `draft` porque é inviável/duplicada. As variáveis (`GEMINI_API_KEY`, `BRAPI_TOKEN` e `DATABASE_URL`) já se encontram declaradas com `sync: false` no arquivo `render.yaml`.
