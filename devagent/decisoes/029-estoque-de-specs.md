# ADR 029 · Estoque de duas specs na fila

- **Data:** 2026-10-29 · **Status:** aceita
- **Revê:** ADR 021 (gatilho do Especificador)

## Contexto

O Especificador só abria sessão com a fila de specs `ready` em 1 ou menos (`FILA_PARA_ESPECIFICAR = 1`). A spec que sobrava era a que o desenvolvimento implementava. Quando ela virava `done`, a próxima ainda precisava ser escrita e revisada (duas sessões e dois PRs), e o desenvolvimento ficava sem trabalho nesse intervalo.

## Decisão

`FILA_PARA_ESPECIFICAR = 2`: o Especificador abre sessão com até duas specs `ready` (revisadas ou à espera da revisão). Assim há sempre uma spec pronta ou a caminho enquanto outra é implementada. O teto diário do Especificador (8 sessões) continua valendo.

## Consequências

- O desenvolvimento não espera o ciclo escrever e revisar a spec seguinte.
- Uma spec a mais fica na fila em média. Com a revisão obrigatória (ADR 021), ela não entra no desenvolvimento antes do Revisor.
