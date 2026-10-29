# ADR 030 · Bug que envelhece ganha prioridade

- **Data:** 2026-10-29 · **Status:** aceita
- **Revê:** ADR 020 (bug na frente), CICLO.md, Passos 1.6 e 6

## Contexto

O Passo 6 (issues abertas) vem depois do Passo 4 (specs) e só roda com a fila de specs vazia. Os achados de severidade baixa do Verificador chegam como `bug` sem `prioridade` (ADR 020) e caem no Passo 6. Com a fila sempre abastecida, eles não eram tratados nunca: em 28/10 a #557 e a #570 esperavam atrás de 12 specs. O próprio `CICLO.md` diz "antes de imaginar qualquer feature nova, esvazie a fila de issues", mas a ordem dos passos impedia.

## Decisão

A varredura do guardião (de hora em hora) aplica o label `prioridade` a toda issue `bug` aberta há mais de 24 h que ainda não o tenha e não esteja `bloqueado`, com um comentário que explica o motivo. Com o label, a issue entra no Passo 1.6, antes da fila de specs, pela regra que já existe (`fila_specs.issue_prioritaria`).

## Consequências

- Nenhum bug espera mais de ~25 h para ser tratado, salvo os `bloqueado`.
- Um dia com muitos bugs antigos atrasa as specs na mesma medida. É a ordem que o `CICLO.md` sempre pediu.
