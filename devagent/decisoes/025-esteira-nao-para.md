# ADR 025 · A esteira não para: relógio de reserva, verificação sem achado e desenvolvedor só com trabalho

- **Data:** 2026-10-29 · **Status:** aceita
- **Revê:** ADRs 010, 012 e 024 (decisão 4)

## Contexto

Uma revisão do fluxo em 28/10 procurou o que deixa a esteira parada ou gastando cota sem entregar:

1. **Um relógio só.** O `jules.yml` não tinha `schedule`: só rodava quando o cron-job.org chamava o `workflow_dispatch` (ADR 010). Um token expirado ou uma queda do serviço parava todas as raias ao mesmo tempo, e só uma pessoa perceberia.
2. **Verificação sem achado segurava a raia.** O job `disciplina` reprova PR `verificação:` sem arquivo novo em `docs/verificacao/achados/` (ADR 024, decisão 4). O guardião, porém, só fechava na hora o PR de especialista sem achado; o de verificação recebia a cobrança `@jules` e ficava aberto até ela vencer, 3 h depois. O #565 ocupou a raia ~4 h, e o #586 (que só marcava um achado antigo como resolvido) também ~4 h. O #569, para passar no CI, registrou um achado sobre o próprio PR, que virou a issue #570.
3. **Desenvolvedor sem trabalho gastava cota.** A rodada iniciava o desenvolvedor sempre que o caminho estava livre, mesmo sem spec revisada, sem issue que ele trate, sem correção no backlog e sem PR travado. A sessão chegava ao Passo 7, que é da raia de especificação, e encerrava sem PR.

## Decisão

1. **Relógio de reserva.** O `jules.yml` ganha `schedule` (`11,41 * * * *`). O cron-job.org continua sendo o relógio principal, a cada 5 min; o do GitHub só garante que a esteira volte sozinha se o principal falhar. Disparos duplicados não causam dano: as execuções são serializadas pelo grupo `jules`.
2. **O guardião fecha na hora PR de verificação sem achado novo**, no CI falho e na varredura, sem cobrar o agente e sem abrir `tentativa-falhou`. Mudar o status de um achado antigo não conta como entrega: a issue do achado já fecha pelo `Closes #N` do PR que corrige. A regra do `conferir_pr` não muda.
3. **O desenvolvedor só começa com trabalho identificável** (`trabalho_do_desenvolvedor` em `devagent/adaptadores/jules.py`): PR do agente travado, issue aberta que não seja `tentativa-falhou`, `bloqueado`, `enhancement` ou `feature`, entrada na seção Correções do backlog, ou spec revisada na fila sem tentativa fechada. Na dúvida (GitHub ou fila ilegíveis), a sessão começa: melhor uma sessão à toa do que a esteira parada. Os especialistas não passam por essa trava; o horário deles continua valendo.

## Consequências

- Com o cron-job.org fora do ar, a esteira anda pelo menos a cada 30 min, conforme os disparos que o GitHub não descartar.
- A raia de verificação fica livre na mesma hora em que um PR sem achado aparece, em vez de 3 a 4 h depois.
- Sem spec revisada e sem issue, nenhuma sessão do desenvolvedor é aberta. O trabalho do Passo 5 (documentação e o próprio agente) passa a acontecer só nas sessões que já tinham outro motivo para existir; um sinal do Passo 5 que precise de sessão própria vira issue.
