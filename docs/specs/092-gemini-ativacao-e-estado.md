---
id: 092
titulo: Gemini ativo e verificado: validar a chave, mostrar o estado real e declarar as variáveis
status: draft
esforco: P
gaveta: saúde técnica
aceite: tests/test_aceite_092.py
---

## Problema

Em `/sistema`, a integração **Gemini** aparece como *Inativo*. A chave `GEMINI_API_KEY` está cadastrada no Render, e o `/api/sistema` de produção de 24/10/2026 confirma: o detalhe diz "sem chamadas desde a partida", texto que o código só usa quando a chave existe (sem chave, o texto seria "sem GEMINI_API_KEY"). O rótulo engana, por três motivos de código:

1. *Inativo* em `app/services/sistema.py::_item_da_fonte` significa "sem chamadas desde a partida", e **não** "sem chave". Com a chave presente e nenhuma chamada, a tela mostra *Inativo, sem chamadas desde a partida*, que é indistinguível de "desligado de propósito".
2. Nenhuma chamada acontece porque o pipeline do Consultor quebra antes de chegar à API (spec 084: tabela `consultor_llm_uso` ausente no Postgres). Corrigir a 084 destrava as chamadas, mas só quando houver matérias na fila e a rodada do coletor passar por `extrair_opinioes`; a tela continua cega até lá.
3. Ninguém valida a chave. O único contato com a API do Gemini é a extração, e `gemini_modelo.modelo_atual` só lista os modelos quando precisa escolher um. Uma chave errada, revogada ou sem permissão só seria descoberta na primeira extração real.

Além disso, `render.yaml` declara só `MT5_API_URL` e `MT5_API_KEY` com `sync: false`. As demais variáveis (`GEMINI_API_KEY`, `GEMINI_MODELO`, `GEMINI_MAX_CHAMADAS_DIA`, `BRAPI_TOKEN`, `DATABASE_URL`) existem só no painel do Render, sem rastro no repositório.

## Comportamento esperado

### Validação ativa da chave

- Ao subir a aplicação e a cada 6 horas, se `GEMINI_API_KEY` existe, o app valida a chave com a chamada que já usa para descobrir o modelo (`GET /v1beta/models`, sem custo de cota de geração) por `gemini_modelo`, e registra o resultado em `registro_fontes` (sucesso ou falha com o status).
- A validação roda em segundo plano, nunca no caminho de uma visita, e respeita o limite de 1 requisição a cada 2 s por domínio.

### Estado real no Sistema

O item Gemini deixa de usar *Inativo* para "chave presente, sem extração ainda". A regra passa a ser:

| Situação | Nível | Texto |
|---|---|---|
| Sem `GEMINI_API_KEY` | Inativo | "sem GEMINI_API_KEY: o Consultor usa só sinais técnicos" |
| Chave recusada (400, 401, 403 na validação ou na extração) | Problema | "chave recusada pelo Gemini (HTTP N)" |
| Chave válida, nenhuma extração ainda, fila vazia | OK | "chave válida, aguardando matérias dos feeds" |
| Chave válida, matérias na fila, nenhuma extração ainda | Atenção | "chave válida, N matérias na fila sem processar" (com o erro da última rodada, se houver) |
| Chave válida e extrações acontecendo | OK | "N de M chamadas hoje · modelo X · última extração às HH:MM" |
| Cota do dia esgotada (status `cota`) | Atenção | "cota diária esgotada, volta amanhã" |

O detalhe traz o modelo escolhido, a cota do dia (`chamadas/GEMINI_MAX_CHAMADAS_DIA`) e a hora da última extração. O texto da tela de Consultor (spec 085) e este item contam a mesma história a partir dos mesmos dados.

### Variáveis declaradas

`render.yaml` passa a declarar, com `sync: false` e sem valores, `GEMINI_API_KEY`, `BRAPI_TOKEN` e `DATABASE_URL`, no mesmo padrão das variáveis do MT5, e o `PRODUTO.md` (tabela de variáveis) cita a validação periódica da chave. O adaptador `devagent/adaptadores/render_blueprint.py` e seus testes continuam verdes.

## Fontes de dados

API do Gemini: `GET /v1beta/models` (validação) e `generateContent` (extração, já existente). Plano B: sem chave ou chave recusada, o Consultor usa só sinais técnicos, com o aviso da spec 085.

## Critérios de aceite

- [ ] Com `GEMINI_API_KEY` definida e a API simulada (respx) respondendo 200 em `/v1beta/models`, a validação registra sucesso e o item do Gemini fica em *OK* sem nenhuma extração.
- [ ] Com 403 simulado na validação, o item fica em *Problema* com o status.
- [ ] Sem a variável, o item fica *Inativo* com o texto do plano B, e nenhuma requisição ao Gemini é feita.
- [ ] Chave válida com matérias na fila e zero extrações: *Atenção* com o número de matérias.
- [ ] Item com extrações mostra cota `N de M`, modelo e horário da última extração.
- [ ] A validação não roda em visita, nem em teste (mesma regra do laço do monitor: desligada com `MONITOR_SISTEMA=0` e sob pytest).
- [ ] `render.yaml` declara as três variáveis com `sync: false`, sem valor, e os testes do adaptador do Render passam.

## Invariantes de produção

- O item Gemini de `/sistema` não aparece como *Inativo* quando `GEMINI_API_KEY` está configurada.
- Em até 6 horas depois do deploy, o item do Gemini traz o resultado de uma validação da chave.

## Fora do escopo

- Trocar o modelo ou o provedor de LLM.
- Mudar a cota diária de chamadas.
- Cadastrar a chave: é do dono do produto, no Render.

## Divisão

Esta spec original foi considerada grande demais e dividida em duas specs menores que podem ser implementadas independentemente:

- **docs/specs/092a-gemini-validacao-e-variaveis.md**: Trata da validação ativa da chave, do registro em `registro_fontes` e da declaração das variáveis em `render.yaml`.
- **docs/specs/092b-gemini-estado-no-sistema.md**: Trata apenas da parte de apresentação (o novo estado real no Sistema), com base no que for feito na 092a e na spec 085.
