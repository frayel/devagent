# Experimento: conclusões parciais

Registro do que o experimento mostrou até agora (objetivo e regras no [`README.md`](../README.md)). Atualize a cada nova rodada de conclusões, mantendo as anteriores com a data.

## Rodada 1 · 2026-10-09 (25/09 a 09/10)

### Números

| Medida | Valor |
|---|---|
| PRs | 174 (160 mesclados, 14 fechados sem merge) |
| Specs concluídas | 31 |
| PRs mesclados por dia | ~11 |
| Commits do agente / do lado humano | 143 / 54 (27% humanos) |
| Commits humanos no código do produto (`app/`) | 16 |
| Issues abertas por robôs (auditoria, deploy, guardião) | 27, 26 fechadas |
| ADRs escritos pelo agente | 0 de 9 |
| Relatórios de execução | 105, dos quais 68 com retrospectiva vazia ou "nenhuma" |

Fontes: histórico do git, API do GitHub (PRs e issues) e `docs/runs/`.

### Prós

- **Execução.** Com uma spec clara, o agente entrega com testes, segue o guia visual e fecha o ciclo sozinho, num ritmo difícil para uma pessoa.
- **Autocorreção com sensor.** Erros objetivos apontados pela auditoria (fuso UTC em vez de BRT, vírgula decimal, fonte ausente, deploy quebrado) são corrigidos sem ajuda. O circuito sensor → issue → correção é a parte mais sólida.
- **Criatividade de produto.** Com o escopo aberto (ADR 003), surgiram painéis que ninguém pediu: Maré do mercado, Scanner de Capitulação, Volatilidade Silenciosa.

### Contras

- **Otimiza para passar na checagem.** Em 03/10, oito PRs quase iguais criaram uma propriedade falsa no gráfico para enganar o auditor, e o falso quebrou a página (ADR 007). O PR vazio #171 passou no CI e foi mesclado.
- **Constrói sobre o que não confere.** Até 27/09 a produção nunca coletou dados e exibia valores de fixtures; o agente seguiu entregando features sobre um banco vazio (ADR 002 e 004).
- **Não aprende com os próprios erros.** Toda regra nova (guardião, Passo 1, disciplina no CI, retomada de ambiente) foi escrita do lado humano. O agente tinha permissão para mudar o próprio processo e não mudou. Muitas retrospectivas copiam o texto do modelo.
- **Gosto precisa de gatilho externo.** O visual só melhorou depois de uma reclamação do dono do produto e de uma regra que obriga a revisão (ADR 006).

### Limitações

- **Relógio.** A tarefa agendada da interface do Jules parava esperando aprovação; o cron do GitHub descarta a maior parte dos disparos frequentes; o vigia contínuo cobrava 1.440 min/dia de Actions dormindo. O relógio passou para o cron-job.org (ADR 010).
- **Sensores agendados também sofrem o descarte.** Em 48 h, a auditoria de produção rodou 6 de 38 vezes previstas. A autocorreção trabalha com uma fração da visão que deveria ter.
- **Infraestrutura gratuita.** O Render hiberna e apaga o disco, misturando falhas da plataforma com falhas do agente.
- **Amostra de um.** Um produto, um agente, duas semanas. Não dá para separar o quanto vem do modelo e o quanto vem dos trilhos.

### Síntese

O experimento mostra autonomia sob trilhos. O agente é um executor rápido e incansável; quem desenhou os trilhos foi o humano, ADR por ADR. Cada intervenção humana é um mapa do ponto em que a autonomia ainda não chega. A pergunta das próximas rodadas é se essa lista para de crescer.
