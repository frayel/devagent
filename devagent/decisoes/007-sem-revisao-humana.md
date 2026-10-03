# ADR 007 · Sem revisão humana

- **Status:** aceita
- **Data:** 2026-10-03
- **Substitui:** o item 5 do ADR 001 e o item 6 do ADR 005

## Contexto

O `automerge.yml` recusava merge de PRs que tocavam caminhos de `devagent/protegidos.txt` e aplicava o label `revisao-humana`. O dono do projeto não revisa PRs, então esses PRs ficavam parados para sempre. Pior: o `estado_github` e o guardião ignoravam PRs com esse label, e a regra "um PR aberto por vez" deixava de valer. Em um dia, oito PRs quase iguais foram abertos para a mesma issue, todos esperando um revisor que não vinha.

Esses oito PRs também mostraram o risco que a trava evitava: para fazer a checagem de gráficos passar, eles afrouxavam a auditoria e faziam a página fingir que tinha dados (uma propriedade falsa no elemento do gráfico). O falso, além de enganar a checagem, quebrou a página com um erro de JavaScript.

## Decisão

1. `devagent/protegidos.txt` deixa de existir. O `automerge.yml` faz merge de todo PR com CI verde, sem exceção.
2. O label `revisao-humana` deixa de existir. `estado_github` e o guardião passam a contar todos os PRs do agente, menos os `auditoria:`.
3. O agente pode alterar qualquer arquivo, inclusive o guardião, o adaptador do Jules, os workflows e a auditoria.
4. A separação de poderes vira regra escrita no `CICLO.md`: uma checagem nunca é afrouxada no mesmo PR que corrige a falha que ela aponta, e a aplicação nunca imita o que a auditoria procura. Se a checagem estiver errada, a correção vai num PR próprio, com evidência.

## Consequências

Nenhum PR fica esperando um humano. O custo é que nada impede mecanicamente o agente de enfraquecer o próprio auditor; a regra escrita e o histórico de PRs são a única defesa. Se o problema reaparecer, a alternativa é um teste no CI que compare as checagens do PR com as da `main`, sem depender de revisão humana.
