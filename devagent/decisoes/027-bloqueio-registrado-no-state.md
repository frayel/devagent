# ADR 027 · Bloqueio registrado no STATE.md, não em comentário de issue

- **Data:** 2026-10-29 · **Status:** aceita
- **Revê:** CICLO.md, Passos 1 e 6 e seção 6

## Contexto

O `CICLO.md` se contradizia. O Passo 6 diz que o agente "não tem permissão para comentar em issues nem para fechá-las", e é assim que a sessão do Jules funciona. Mas o Passo 1, a tabela do Passo 6 e a seção 6 mandavam "comentar na issue o ajuste exato", "aplicar o label `bloqueado`", "abrir uma issue `bloqueado`" e "pedir ajuda na issue". Nenhum workflow aplica `bloqueado` (o `auditoria-producao.yml` só o remove), então essas instruções pediam o impossível, e a sessão que chegava nelas não tinha caminho válido.

## Decisão

1. Um bloqueio que depende de pessoa vai para a seção *Bloqueios* do `docs/STATE.md`, com o ajuste exato, num PR `docs:` que cita a issue com `Refs #N` (sem `Closes`, para ela não fechar antes da hora).
2. Quem aplica `bloqueado` é o dono do produto, ao ler esse PR. O ciclo continua pulando as issues com o label.
3. Entrada da seção *Correções* que depende de pessoa leva a palavra `bloqueado` no texto, que já basta para o `conferir_pr` e a fila a pularem.

## Consequências

- O registro do bloqueio passa pelo CI e fica versionado, em vez de se perder num comentário.
- Até o dono aplicar o label, a issue continua contando como trabalho (ADR 025), e uma sessão pode encontrá-la de novo. O registro no `STATE.md` diz a essa sessão que o bloqueio já foi descrito.
