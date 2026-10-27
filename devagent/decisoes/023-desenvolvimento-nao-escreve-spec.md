# ADR 023 · O desenvolvimento não cria, não divide e não edita specs

- **Data:** 2026-10-27 · **Status:** aceita
- **Revê:** ADR 021 (itens 4 e 5), ADR 018 (quem divide a spec com tentativa fechada) e os Passos 4 e 6 do `CICLO.md`

## Contexto

Com as raias do ADR 021, o desenvolvimento ainda escrevia spec em três situações: ao transformar issue de feature em spec (Passo 6), ao dividir spec grande demais (Passo 4) e ao dividir spec com `tentativa-falhou`. O Revisor também edita e divide specs. As duas raias passaram a mexer nos mesmos `.md` de `docs/specs/` ao mesmo tempo, e os PRs entraram em conflito (#542 e #543, duas divisões da 092a).

## Decisão

1. Specs são das raias de especificação e de revisão. O desenvolvimento não cria, não divide, não apaga e não edita specs. O único toque permitido é trocar a linha `status:` para `done` no PR da entrega.
2. A regra 8 do `conferir_pr` reprova, na raia de desenvolvimento, spec nova, spec apagada, texto de spec alterado e status trocado para outra coisa que não `done` (`raias.edicao_de_spec_proibida`).
3. Issue de feature vira spec pelo Especificador, antes do Passo 7.
4. Spec com `tentativa-falhou` é dividida pelo Revisor: a rodada abre a sessão dele com a spec e as issues no prompt, e o PR `revisão:` as fecha. O desenvolvimento pula essa spec e segue para os Passos 5 e 6.
5. O prompt do desenvolvimento não traz mais número de spec reservado.

## Consequências

- `docs/specs/` deixa de ser disputado entre o desenvolvimento e as raias auxiliares.
- Spec grande demais que o Revisor deixou passar só é dividida depois de uma tentativa fechada pelo guardião; o Revisor já mede o tamanho antes de aprovar.
