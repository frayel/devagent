---
id: 092b
titulo: Mostrar o estado real do Gemini no sistema
status: draft
esforco: P
gaveta: saúde técnica
aceite: tests/test_aceite_092b.py
revisada: 2026-10-27
---

## Problema

"Por que a integração com o Gemini aparece como Inativo no sistema se a chave está configurada e as requisições estão acontecendo?"

Em `/sistema`, a integração **Gemini** aparece como *Inativo*. O `/api/sistema` de produção de 24/10/2026 confirma: o detalhe diz "sem chamadas desde a partida", texto que o código só usa quando a chave existe (sem chave, o texto seria "sem GEMINI_API_KEY"). O rótulo engana, por motivos de código:

1. *Inativo* em `app/services/sistema.py::_item_da_fonte` significa "sem chamadas desde a partida", e **não** "sem chave". Com a chave presente e nenhuma chamada, a tela mostra *Inativo, sem chamadas desde a partida*, que é indistinguível de "desligado de propósito".
2. Nenhuma chamada acontece porque o pipeline do Consultor quebra antes de chegar à API (spec 084: tabela `consultor_llm_uso` ausente no Postgres). Corrigir a 084 destrava as chamadas, mas só quando houver matérias na fila e a rodada do coletor passar por `extrair_opinioes`; a tela continua cega até lá.

Depende da spec 092a (que implementa a validação da chave em `registro_fontes`).

## Comportamento esperado

### Estado real no Sistema

O item Gemini deixa de usar *Inativo* para "chave presente, sem extração ainda". A regra passa a ser baseada em `registro_fontes` e na fila de matérias:

| Situação | Nível | Texto |
|---|---|---|
| Sem `GEMINI_API_KEY` | Inativo | "sem GEMINI_API_KEY: o Consultor usa só sinais técnicos" |
| Chave recusada (400, 401, 403 na validação ou na extração) | Problema | "chave recusada pelo Gemini (HTTP N)" |
| Chave válida, nenhuma extração ainda, fila vazia | OK | "chave válida, aguardando matérias dos feeds" |
| Chave válida, matérias na fila, nenhuma extração ainda | Atenção | "chave válida, N matérias na fila sem processar" (com o erro da última rodada, se houver) |
| Chave válida e extrações acontecendo | OK | "N de M chamadas hoje · modelo X · última extração às HH:MM" |
| Cota do dia esgotada (status `cota`) | Atenção | "cota diária esgotada, volta amanhã" |

O detalhe traz o modelo escolhido, a cota do dia (`chamadas/GEMINI_MAX_CHAMADAS_DIA`) e a hora da última extração. O texto da tela de Consultor (spec 085) e este item contam a mesma história a partir dos mesmos dados.

## Fontes de dados

API do Gemini: `generateContent` (extração, já existente). Plano B: sem chave ou chave recusada, o Consultor usa só sinais técnicos, com o aviso da spec 085.

## Critérios de aceite

- [ ] Com `GEMINI_API_KEY` definida e sucesso na validação (mock de `registro_fontes`), o item do Gemini fica em *OK* sem nenhuma extração.
- [ ] Com 403 (na validação ou extração), o item fica em *Problema* com o status.
- [ ] Sem a variável, o item fica *Inativo* com o texto do plano B.
- [ ] Chave válida com matérias na fila e zero extrações: *Atenção* com o número de matérias.
- [ ] Item com extrações mostra cota `N de M`, modelo e horário da última extração.

## Invariantes de produção

- O item Gemini de `/sistema` não aparece como *Inativo* quando `GEMINI_API_KEY` está configurada.
- Em até 6 horas depois do deploy, o item do Gemini traz o resultado de uma validação da chave.

## Fora do escopo

- Validação da chave em segundo plano e variáveis em render.yaml (feito na 092a).
- Trocar o modelo ou o provedor de LLM.
- Mudar a cota diária de chamadas.

## Revisão

Spec movida para `draft` por depender de uma funcionalidade ainda não implementada na `main`. A spec afirma "Depende da spec 092a (que implementa a validação da chave em registro_fontes)", mas a 092a ainda não foi implementada pelo desenvolvimento. O Revisor não aprova specs baseadas em promessas de código futuro ou dependentes de specs não implementadas na mesma entrega.
