# ADR 020 · Issue que nenhum passo lê é fechada, e bug da auditoria passa na frente da fila

- **Data:** 2026-10-23 · **Status:** aceita
- **Complementa:** ADRs 015, 018 e 019

## Contexto

Em 23/10 havia três issues abertas que o ciclo via em todo `estado_github` e nunca tratava.

1. **Bug atrás da fila de specs.** A auditoria abriu a #418 (data incompleta em parte da tela) com os labels `auditoria` e `bug`. Bugs comuns ficam no Passo 6, que só roda com a fila de specs vazia. A fila tinha cinco specs `ready`, o prompt da sessão (ADR 015) mandava implementar a próxima, e o próprio agente acrescenta specs. O Passo 6 não chegava. O label `prioridade`, que o Passo 1.6 trata antes da fila, nunca era aplicado: nem existia no repositório.
2. **Tentativa de spec já entregue.** A #416 registrou o fechamento do #415 (spec 076b) por conflito. A 076b foi entregue no #414 sem `Closes #416`. O ciclo só lê `tentativa-falhou` da próxima spec da fila, e a issue nem trazia o número da spec (o título dizia "lote 3 parte b"). Com a spec `done`, nada a fecharia.
3. **Especialista vazio registrado como falha.** O #426 (Sentinel) não trazia nenhum arquivo. O ADR 019 só isentava o PR de especialista que trouxesse o diário, então o guardião abriu a #427. Ela não cita spec, e nenhum passo a consome.

## Decisão

1. **Achado de auditoria de severidade média ou baixa nasce com `prioridade`.** Entra no Passo 1.6, antes do Passo 4. Alta continua com `producao-incorreta`, no Passo 1.
2. **A issue `prioridade` mais antiga vai no prompt e no `estado_github`.** `fila_specs.instrucao` diz para corrigi-la num PR `fix:` com `Closes` e não implementar spec nesta sessão. Sem isso, a frase da fila (ADR 015) continuaria mandando para a spec.
3. **A `tentativa-falhou` registra a spec do PR.** Por extenso ("spec 076b", que o `fila_specs` casa) e num marcador `<!-- spec: 076b -->`. A spec vem do título, do corpo, da branch e dos arquivos de spec que o PR altera.
4. **O guardião fecha `tentativa-falhou` órfã** a cada varredura: quando todas as specs citadas estão `done` na `main`, ou quando a issue não cita spec nenhuma. Issues antigas sem marcador têm as specs lidas dos arquivos do PR fechado. Issues `bloqueado` ficam abertas.
5. **PR de especialista vazio é especialista sem achado.** Fecha sem issue, como o que só traz o diário.

## Consequências

- Um bug apontado pela auditoria atrasa a fila de specs em uma sessão. É a troca desejada: o que está errado na tela vem antes do que ainda não existe.
- Se a auditoria marcar como bug algo que é gosto, a sessão gasta uma rodada nisso. A tabela do Passo 6 continua valendo para classificar a issue.
- Uma tentativa sem spec perde a lição que trazia. O motivo continua na issue fechada e no relatório da execução, e nenhum passo a lia antes.
