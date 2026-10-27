---
id: 120b
titulo: Validar a chave da API do Gemini ativamente
status: ready
esforco: M
gaveta: saúde técnica
aceite: tests/test_aceite_120b.py
revisada: 2026-10-27
---

## Problema

Como sabemos se a chave do Gemini configurada ainda funciona sem esperar o momento de uma extração real de conteúdo?

A chave `GEMINI_API_KEY` está configurada, mas o único contato com a API do Gemini é a extração e descoberta de modelos de forma "preguiçosa". Uma chave errada, revogada ou sem permissão só seria descoberta na primeira extração real.

## Comportamento esperado

- Ao subir a aplicação e a cada 6 horas, se `GEMINI_API_KEY` existe, o app valida a chave com a chamada que já usa para descobrir o modelo (`GET /v1beta/models`) e registra o resultado em `registro_fontes` (sucesso ou falha com o status).
- A validação roda em segundo plano, nunca no caminho de uma visita, e respeita o limite de 1 requisição a cada 2 s por domínio.
- O `PRODUTO.md` (tabela de variáveis) cita a validação periódica da chave.

## Testes tocados
- `tests/test_aceite_120b.py` (novo)
- `tests/test_agendador.py` (se a validação for incluída lá) (1)

Total: 2 testes tocados.

## Fontes de dados

API do Gemini: `GET /v1beta/models` (validação). Plano B: sem chave ou chave recusada, o sistema continua rodando e marca a fonte como inativa.

## Cálculos

N/A

## Critérios de aceite

- [ ] Com `GEMINI_API_KEY` definida e a API simulada (respx) respondendo 200 em `/v1beta/models`, a validação registra sucesso em `registro_fontes`.
- [ ] Com 403 simulado na validação, a validação registra falha em `registro_fontes`.
- [ ] Sem a variável, nenhuma requisição ao Gemini é feita na validação.
- [ ] A validação não roda em visita, nem em teste (desligada com `MONITOR_SISTEMA=0` e sob pytest).

## Invariantes de produção

- A tabela de banco de dados registra sucesso ou erro a cada 6 horas para as chaves presentes, mantendo visibilidade da validade no sistema.

## Fora do escopo

- Alterar a interface do `/sistema` e o texto do painel do Gemini (será feito na spec 092b).
- Declaração de variáveis no render.yaml (feita na spec 120a).
