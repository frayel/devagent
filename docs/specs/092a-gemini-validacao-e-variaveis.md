---
id: 092a
titulo: Gemini ativo, validar a chave, declarar as variáveis
status: draft
esforco: P
gaveta: saúde técnica
aceite: tests/test_aceite_092a.py
revisada: 2026-10-26
---

## Problema

Como sabemos se a chave do Gemini configurada ainda funciona sem esperar o momento de uma extração real de conteúdo?

Em `/sistema`, a integração **Gemini** aparece como *Inativo*. A chave `GEMINI_API_KEY` está cadastrada no Render, mas ninguém valida a chave. O único contato com a API do Gemini é a extração, e `gemini_modelo.modelo_atual` só lista os modelos quando precisa escolher um. Uma chave errada, revogada ou sem permissão só seria descoberta na primeira extração real.

Além disso, `render.yaml` declara só `MT5_API_URL` e `MT5_API_KEY` com `sync: false`. As demais variáveis (`GEMINI_API_KEY`, `GEMINI_MODELO`, `GEMINI_MAX_CHAMADAS_DIA`, `BRAPI_TOKEN`, `DATABASE_URL`) existem só no painel do Render, sem rastro no repositório.

## Comportamento esperado

### Validação ativa da chave

- Ao subir a aplicação e a cada 6 horas, se `GEMINI_API_KEY` existe, o app valida a chave com a chamada que já usa para descobrir o modelo (`GET /v1beta/models`, sem custo de cota de geração) por `gemini_modelo`, e registra o resultado em `registro_fontes` (sucesso ou falha com o status).
- A validação roda em segundo plano, nunca no caminho de uma visita, e respeita o limite de 1 requisição a cada 2 s por domínio.

### Variáveis declaradas

`render.yaml` passa a declarar, com `sync: false` e sem valores, `GEMINI_API_KEY`, `BRAPI_TOKEN` e `DATABASE_URL`, no mesmo padrão das variáveis do MT5, e o `PRODUTO.md` (tabela de variáveis) cita a validação periódica da chave. O adaptador `devagent/adaptadores/render_blueprint.py` e seus testes continuam verdes.

## Fontes de dados

API do Gemini: `GET /v1beta/models` (validação). Plano B: sem chave ou chave recusada, o Consultor usa só sinais técnicos, com o aviso da spec 085.

## Critérios de aceite

- [ ] Com `GEMINI_API_KEY` definida e a API simulada (respx) respondendo 200 em `/v1beta/models`, a validação registra sucesso em `registro_fontes`.
- [ ] Com 403 simulado na validação, a validação registra falha em `registro_fontes`.
- [ ] Sem a variável, nenhuma requisição ao Gemini é feita na validação.
- [ ] A validação não roda em visita, nem em teste (mesma regra do laço do monitor: desligada com `MONITOR_SISTEMA=0` e sob pytest).
- [ ] `render.yaml` declara as três variáveis com `sync: false`, sem valor, e os testes do adaptador do Render passam.

## Invariantes de produção

- A tabela de banco de dados registra sucesso ou erro a cada 6 horas para as chaves presentes, mantendo visibilidade da validade.
- `render.yaml` mantém declaração sem valor das variáveis de ambiente de chaves.

## Fora do escopo

- Alterar a interface do `/sistema` e o texto do painel do Gemini (será feito na spec 092b).
- Trocar o modelo ou o provedor de LLM.
- Mudar a cota diária de chamadas.
- Cadastrar a chave: é do dono do produto, no Render.

## Dividida em
Devido ao tamanho e testes tocados, foi dividida em:
- `119a`: Declarar as variáveis no render.yaml
- `119b`: Validação ativa da chave do Gemini
