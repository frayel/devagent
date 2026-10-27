---
id: 119b
titulo: Gemini ativo, validar a chave
status: ready
esforco: M
gaveta: saúde técnica
aceite: tests/test_aceite_119b.py
revisada: 2026-10-27
---

## Problema

Como sabemos se a chave do Gemini configurada ainda funciona sem esperar o momento de uma extração real de conteúdo?

Em `/sistema`, a integração **Gemini** aparece como *Inativo*. A chave `GEMINI_API_KEY` está cadastrada no Render, mas ninguém valida a chave. O único contato com a API do Gemini é a extração, e `gemini_modelo.modelo_atual` só lista os modelos quando precisa escolher um. Uma chave errada, revogada ou sem permissão só seria descoberta na primeira extração real.

## Comportamento esperado

### Validação ativa da chave

- Ao subir a aplicação e a cada 6 horas, se `GEMINI_API_KEY` existe, o app valida a chave com a chamada que já usa para descobrir o modelo (`GET /v1beta/models`, sem custo de cota de geração) por `gemini_modelo`, e registra o resultado em `registro_fontes` (sucesso ou falha com o status).
- A validação roda em segundo plano, nunca no caminho de uma visita, e respeita o limite de 1 requisição a cada 2 s por domínio.

## Fontes de dados

API do Gemini: `GET /v1beta/models` (validação). Plano B: sem chave ou chave recusada, o Consultor usa só sinais técnicos, com o aviso da spec 085.

## Critérios de aceite

- [ ] Com `GEMINI_API_KEY` definida e a API simulada (respx) respondendo 200 em `/v1beta/models`, a validação registra sucesso em `registro_fontes`.
- [ ] Com 403 simulado na validação, a validação registra falha em `registro_fontes`.
- [ ] Sem a variável, nenhuma requisição ao Gemini é feita na validação.
- [ ] A validação não roda em visita, nem em teste (mesma regra do laço do monitor: desligada com `MONITOR_SISTEMA=0` e sob pytest).

## Invariantes de produção

- A tabela de banco de dados registra sucesso ou erro a cada 6 horas para as chaves presentes, mantendo visibilidade da validade.

## Fora do escopo

- Alterar a interface do `/sistema` e o texto do painel do Gemini.
- Trocar o modelo ou o provedor de LLM.
- Mudar a cota diária de chamadas.
- Declarar as variáveis no `render.yaml` (feito na spec 119a).
