# ADR 021 · Raias paralelas: especificação, revisão e verificação ao lado do desenvolvimento

- **Data:** 2026-10-23 · **Status:** aceita
- **Revê:** a regra de um PR aberto do agente por vez (agora, um por raia) e o Passo 7 no ciclo do desenvolvedor
- **Complementa:** ADRs 012 e 015

## Contexto

Com o ADR 012 o ritmo deixou de ser o relógio e passou a ser a duração de uma volta completa: sessão, CI e auto-merge, uma de cada vez. O plano do executor permite várias sessões simultâneas e o ciclo usava uma. Tudo passava pela mesma fila: escrever spec, implementar, conferir. Enquanto o desenvolvedor escrevia uma spec no Passo 7, nada era implementado; enquanto implementava, ninguém olhava com distância o que já tinha sido entregue nem a spec que viria a seguir.

O dono do projeto pediu mais ritmo com paralelismo, mantendo o desenvolvimento como tarefa única, e limitou as raias a quatro: desenvolvimento, especificação, um revisor de spec e um verificador geral.

O risco do paralelismo é o conflito. Ele só nasce onde duas sessões escrevem no mesmo lugar.

## Decisão

1. **O trabalho é dividido pelo que cada raia escreve** (`devagent/raias.py`). A raia de um PR sai do prefixo do título:

   | Raia | Prefixo | Pode alterar |
   |---|---|---|
   | desenvolvimento | os demais | tudo, menos `docs/verificacao/` |
   | especificação | `spec:` | `docs/specs/`, `docs/BACKLOG.md`, `docs/STATE.md`, `docs/runs/` |
   | revisão | `revisão:` | `docs/specs/`, `docs/runs/` |
   | verificação | `verificação:` | `docs/verificacao/` |

   A regra 8 do `conferir_pr` reprova o PR que sai da sua faixa.
2. **Cada raia tem no máximo uma sessão ativa e um PR aberto.** A regra de continuidade passa a valer por raia. Os especialistas continuam dentro da raia de desenvolvimento, um por vez, porque alteram código.
3. **Uma spec passa pelas três raias em ordem, nunca por duas ao mesmo tempo.** O Especificador a escreve sem `revisada:`; o Revisor a revisa e preenche o campo; só então ela entra na fila do desenvolvimento (`fila_specs.fila_do_desenvolvimento`). Vale a partir de `revisao_obrigatoria_desde` no `devagent.toml`; as specs anteriores seguem como estavam.
4. **O Passo 7 sai do ciclo do desenvolvedor e vira a raia de especificação.** A rodada abre o Especificador quando a fila de specs `ready` chega a uma, a que o desenvolvimento está implementando: a próxima fica pronta quando a atual termina. Fica mantido o espírito do ADR 015 (não acumular specs): o Especificador nunca roda com duas ou mais specs na fila.
5. **Números de spec são reservados antes da sessão.** O desenvolvimento ainda escreve spec no Passo 6 (pedido de feature numa issue), ao mesmo tempo que o Especificador. A rodada põe no prompt de cada sessão "use o número NNN", pulando os números prometidos a sessões das últimas 12 h; assim dois arquivos novos nunca colidem.
6. **O verificador geral olha o que o desenvolvimento mesclou**, no mínimo 90 min depois da verificação anterior. Os achados vão para `docs/verificacao/achados/` e viram issues `verificacao` pelo mesmo caminho dos achados do auditor; `alta` e `media` ganham `prioridade` e passam na frente da fila de specs (ADR 020). Sem achado, não há PR.
7. **PR de raia paralela fechado pelo guardião não abre `tentativa-falhou`.** Não há spec a dividir; a raia recomeça na rodada seguinte.

## Consequências

- Até quatro sessões simultâneas no executor, das quais só uma altera código.
- A cota diária é dividida entre as raias. O ritmo calculado do desenvolvedor não mudou; se a cota apertar, a reserva de 4 tarefas para especialistas e auditor continua protegida, e quem para primeiro são o desenvolvedor e as raias paralelas.
- O desenvolvedor pode ficar sem trabalho enquanto a única spec da fila espera o Revisor. Nessa volta ele trata issues e documentação (Passos 5 e 6) ou encerra sem PR.
- Conflitos ainda possíveis, e pequenos: o Especificador e o desenvolvimento podem tocar o `docs/STATE.md` e o `docs/BACKLOG.md` na mesma janela. O guardião trata como qualquer conflito pequeno (ADR 017).
- O verificador cobra cota mesmo quando não acha nada. O intervalo de 90 min limita o custo a no máximo 16 sessões por dia.
