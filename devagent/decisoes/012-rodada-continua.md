# ADR 012 · Rodada contínua e execução sem entrega

- **Data:** 2026-10-18 · **Status:** aceita
- **Revê:** a frequência de 30 min e a regra de uma sessão por hora do ADR 010

## Contexto

Com o ADR 010, o cron-job.org chamava a rodada a cada 30 min, e a rodada só iniciava uma sessão por hora cheia (`ja_iniciada_nesta_hora`). Duas consequências apareceram:

1. **Teto de 24 sessões por dia, independente da cota.** Uma sessão que terminava em 15 min deixava o agente parado o resto da hora. O especialista que encontrava o desenvolvedor ocupado na sua hora perdia o dia.
2. **PRs sem entrega.** O #326 (Sentinel) só trazia a linha do diário dizendo que não havia nada a fazer: a regra 7 dos especialistas mandava encerrar sem PR, mas a regra 6 mandava escrever o diário, e o Jules abre PR para qualquer alteração. No ciclo do desenvolvedor, os Passos 3 e 6 terminavam a execução mesmo quando não tinham produzido nada, e o relatório obrigatório virava um PR vazio de conteúdo.

O dono do projeto pediu mais frequência, já que o repositório é público (minutos do Actions sem custo), e que um ciclo sem nada a fazer passe direto ao próximo passo em vez de esperar o próximo disparo.

## Decisão

1. **O cron-job.org chama a rodada a cada 5 min.** Cada rodada leva segundos; as execuções do `jules.yml` são serializadas pelo grupo de concorrência.
2. **A rodada inicia a próxima sessão quando o caminho estiver livre**, sem trava por hora:
   - nenhuma sessão que altera código ativa (regra que já existia);
   - nenhum PR do agente com CI rodando, sem CI ainda, ou verde há menos de 60 min (o auto-merge vai mesclar; uma sessão nova só acharia o PR aberto e sairia);
   - o ritmo da cota: `JULES_INTERVALO_MINUTOS`, se definido; senão 24 h / (`JULES_LIMITE_DIARIO` − 4), para a cota não ser gasta numa rajada e deixar o agente parado até a janela de 24 h andar.
3. **O especialista do dia vira o primeiro da fila a partir da sua hora** e fica lá até rodar. PR do agente travado (CI falhou, ou verde há mais de 60 min) chama o desenvolvedor, nunca o especialista.
4. **Execução sem entrega não existe** (`CICLO.md`, seção 4): passo que não gera mudança segue para o próximo na mesma sessão; o relatório vai no PR da entrega.
5. **Especialista sem achado vira desenvolvedor** na mesma sessão (regra 7 de `especialistas.md`), levando a linha do diário no PR do ciclo. A tarefa da cota não se perde.
6. **A regra 6 do `conferir_pr`** reprova PR que só altera `docs/runs/` e `.jules/`, salvo quando o corpo fecha issues (`Closes #N`).

## Consequências

- Quantas sessões por hora: o limite deixa de ser o relógio. Passa a ser o menor entre a duração de uma volta completa (sessão + CI + auto-merge, porque só um PR do agente fica aberto por vez) e a cota do plano do Jules (15, 100 ou 300 tarefas por 24 h; 3, 15 ou 60 simultâneas, das quais o ciclo usa uma).
- Sem `JULES_LIMITE_DIARIO` definido, não há ritmo: no plano gratuito as 15 tarefas acabam em poucas horas e o agente fica parado até a janela andar. Definir a variável é o recomendado.
- 288 rodadas por dia no Actions, cada uma com menos de 1 min, sem custo em repositório público. Num repositório privado, voltar para 15 ou 30 min.
- A rodada faz uma leitura a mais no GitHub (PRs abertos e check-runs). Se ela falhar, a rodada não inicia sessão e ainda destrava; a próxima volta tenta de novo em 5 min.
- O auditor continua abrindo o PR `auditoria:` diário mesmo com 0 achados: é o registro de que a auditoria rodou, não conta na fila do agente e não é afetado pela regra 6 (`docs/auditoria/` não é registro de execução).
