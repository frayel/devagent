# ADR 015 · A próxima spec vai no prompt da sessão

- **Data:** 2026-10-19 · **Status:** aceita
- **Complementa:** ADR 012

## Contexto

Em 19/10, com doze specs `ready` na `main` (068b a 079), o Jules abriu o PR #356, que gerou ideias e escreveu a spec 081 pelo Passo 7. O CICLO.md diz que o Passo 7 só se aplica quando não há spec `ready`, mas o relatório da rodada nem menciona a fila: a sessão conferiu produção, PRs e cadências e foi direto ao Passo 7. Pouco antes, a spec 080 tinha sido implementada (#353) com a 068b ainda esperando.

A ordem do ciclo dependia só da leitura do agente. Com a pressão por entrega da ADR 012, escrever uma spec é o caminho mais barato que ainda conta como PR. Reprovar o PR no CI chegaria tarde: a sessão já teria gasto a cota, e o PR travaria o ciclo até ser fechado.

## Decisão

A escolha da próxima spec sai do agente e vai para código, antes da sessão começar:

- `devagent/fila_specs.py` lista as specs `ready` em ordem natural (068a, 068b, 069, ..., 080).
- O vigia (`adaptadores/jules.py`, `prompt_de`) acrescenta ao prompt do desenvolvedor qual é a próxima spec e que, com a fila não vazia, a sessão não escreve spec nova nem roda o Passo 7. Os passos 1 e 2 continuam na frente.
- `estado_github`, o primeiro comando de toda execução, mostra a fila e repete a instrução quando não há PR do agente aberto.

## Consequências

- O Passo 7 só acontece com a fila vazia, e a ordem de implementação deixa de depender de quem escolhe.
- Ideias novas esperam a fila esvaziar. Pedidos do dono do produto chegam por issue (Passo 6) e viram spec mesmo com fila, como antes.
- O prompt passa a depender do checkout da `main` no job do vigia, que o `jules.yml` já faz. Sem a pasta de specs, o prompt volta ao texto fixo.
