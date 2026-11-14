# ADR 033 · O papel da sessão sai do código, e raia parada não deixa o ciclo ocioso

- **Data:** 2026-11-14 · **Status:** aceita
- **Revê:** ADRs 021, 024, 029, 032; CICLO.md (seção 4); agents/raias.md

## Contexto

As raias paralelas (ADR 021) dependem umas das outras: o desenvolvimento só implementa spec com `revisada:`, e só o Revisor escreve esse campo. Até o ADR 032, um orquestrador externo abria a sessão de cada raia e punha o alvo no prompt. A migração desligou o orquestrador e deixou escrito que as raias "rodam em tarefas agendadas próprias", mas essas tarefas não foram criadas. Sobrou uma tarefa agendada, a do desenvolvedor.

De 13/11 20:47 a 14/11 12:49 a `main` recebeu dezessete PRs seguidos sem fechar nenhuma spec, com oito specs `ready` esperando revisão. O desenvolvedor viu o bloqueio (os relatórios de 05:38 em diante o citam, até "décima rodada seguida") e não pôde agir: a regra *Execução sem entrega não existe* o empurrava para o Passo 5, a retrospectiva de cada rodada propunha a melhoria da seguinte, e nenhuma instrução dizia o que fazer quando o bloqueio é de outra raia. O dono do produto só soube ao perguntar.

Três defeitos se somaram: a decisão de quem trabalha morava fora do repositório; o ciclo não tinha saída para raia parada; o bloqueio não chegava a ninguém.

## Decisão

1. **O papel da sessão é decidido por `devagent/papel.py`**, com funções puras e testadas. O `estado_github` imprime a decisão no primeiro comando. A sessão que ninguém nomeou é do desenvolvedor, salvo quando ele não tem trabalho de produto (produção, PR aberto, issue `prioridade`, spec revisada) e outra raia segura a fila: aí a sessão **assume essa raia por inteiro**, com a persona de `agents/raias.md` e o marcador da raia, revisão antes de especificação. Uma tarefa agendada só já mantém todas as raias andando.
2. **O alvo das raias sai do mesmo módulo.** `python -m devagent.papel revisor | especificador | verificador` diz o alvo da persona nomeada (a spec a revisar, o número reservado, os merges a verificar) ou manda encerrar. O prompt da tarefa agendada fica fixo e curto.
3. **PR travado de raia paralela vira tarefa da raia.** CI falhando ou conflito num PR `spec:`, `revisão:` ou `verificação:` é o alvo da próxima sessão dessa raia, na branch dele.
4. **Fila travada tem alarme e tem fim.** Com spec `ready` na fila e quatro entregas seguidas do desenvolvimento sem fechar nenhuma, o `estado_github` imprime `FILA TRAVADA`. A entrega da sessão passa a ser destravar: causa no repositório se corrige; causa fora dele vai uma única vez para *Bloqueios* do estado do sistema. Com o bloqueio registrado, a sessão encerra sem PR.
5. **O Passo 5 não é refúgio.** Ele não se aplica enquanto a fila está travada, e bloqueio de outra raia nunca fica só na retrospectiva.

A sessão continua tendo uma persona só do começo ao fim, como pede o ADR 024: o que muda é que a escolha vem do estado do repositório, e não do horário nem do juízo da sessão. O #823 tirou da skill `/ciclo` a troca de persona por horário; esta decisão não a traz de volta.

## Consequências

- Uma raia sem tarefa agendada atrasa o fluxo, mas não o para: a sessão do desenvolvedor a cobre na volta seguinte.
- Com uma tarefa só, revisão e implementação se alternam, e o ritmo cai à metade. As tarefas próprias das raias (`OPERACAO.md`) devolvem o ritmo inteiro, e a verificação só roda com a tarefa dela.
- O Revisor pode ser a mesma sessão agendada que, na volta seguinte, implementa. A independência que importa se mantém: quem revisa não é quem escreveu a spec, e as sessões não compartilham memória.
- A janela do Verificador sai do último relatório versionado, limitada a 24 h. Verificação sem achado não deixa relatório, então a tarefa dele roda uma vez por dia para não repetir trabalho.
