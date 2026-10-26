---
id: 2026-10-26-spec-089-nao-aponta-partes
severidade: media
painel: docs/specs/089-consultor-data-de-referencia.md
status: aberto
visto_em: 2026-10-26T00:00-03:00
pr: 507
---

# Spec 089 dividida não diz para onde foram as partes

## O que acontece
No PR 507, a especificação 089 (`docs/specs/089-consultor-data-de-referencia.md`) foi dividida nas specs 113a e 113b. O arquivo 089 teve seu status alterado para `draft`, mas o texto da spec não foi atualizado para indicar que ela foi dividida, nem para quais arquivos as partes foram movidas.

## O que deveria acontecer
Segundo as regras do Revisor em `devagent/agents/raias.md`: "grande demais: divida em NNNa, NNNb, ... (cada parte já revisada), marque a original como draft e diga na original para onde foi cada parte;". O texto original deveria conter uma menção clara para onde foi cada parte.

## Evidência
Lendo o conteúdo de `docs/specs/089-consultor-data-de-referencia.md` no commit 15549fb, não há nenhuma menção às specs 113a ou 113b.

## Como reproduzir
Ler o arquivo `docs/specs/089-consultor-data-de-referencia.md`.
