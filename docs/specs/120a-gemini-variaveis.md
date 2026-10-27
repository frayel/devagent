---
id: 120a
titulo: Declarar as variáveis de ambiente adicionais
status: draft
esforco: P
gaveta: saúde técnica
aceite: tests/test_aceite_120a.py
revisada: 2026-10-27
---

## Problema

O arquivo `render.yaml` declara só `MT5_API_URL` e `MT5_API_KEY` com `sync: false`. As demais variáveis (`GEMINI_API_KEY`, `GEMINI_MODELO`, `GEMINI_MAX_CHAMADAS_DIA`, `BRAPI_TOKEN`, `DATABASE_URL`) existem só no painel do Render, sem rastro no repositório.

## Comportamento esperado

`render.yaml` passa a declarar, com `sync: false` e sem valores, `GEMINI_API_KEY`, `BRAPI_TOKEN` e `DATABASE_URL`, no mesmo padrão das variáveis do MT5. O adaptador `devagent/adaptadores/render_blueprint.py` e seus testes continuam verdes.

## Testes tocados
- `tests/test_aceite_120a.py` (novo)
- `devagent/tests/test_render_blueprint.py` (1)

Total: 2 testes tocados.

## Fontes de dados

N/A.

## Cálculos

N/A.

## Critérios de aceite

- [ ] `render.yaml` declara as três variáveis com `sync: false`, sem valor.
- [ ] Os testes do adaptador do Render (`devagent/tests/test_render_blueprint.py`) passam após a alteração no YAML.

## Invariantes de produção

- `render.yaml` mantém declaração sem valor das variáveis de ambiente de chaves e o sistema não expõe os valores reais.

## Fora do escopo

- Validação periódica da chave (movida para a spec 120b).
- Alterar o provedor de LLM.

## Revisão

Duplicata da 119a, nascida da segunda divisão da 092a (#543, paralela ao #542). As variáveis `GEMINI_API_KEY`, `BRAPI_TOKEN` e `DATABASE_URL` já estão declaradas com `sync: false` no `render.yaml`; não há trabalho a fazer. (ADR 024)
