# ADR 010 · Relógio externo para o Jules (cron-job.org)

- **Status:** aceita
- **Data:** 2026-10-08
- **Substitui:** o job `vigia` contínuo do `jules.yml` (introduzido em 2026-10-01)

## Contexto

O Jules não tem agenda própria confiável pela API: alguém precisa, de tempos em tempos, iniciar a persona da hora e destravar sessões paradas em aprovação de plano ou em pergunta. Esse "alguém" foi, em sequência:

1. **Tarefa agendada da interface do Jules.** Parava em "aguardando aprovação do plano" mesmo com o prompt pedindo o contrário. Substituída pela API (`devagent/adaptadores/jules.py`).
2. **`schedule` do GitHub Actions.** O cron do GitHub não é relógio. Em 30/09 e 01/10 executou cerca de 1 em cada 10 disparos agendados, com buracos de até 3,5 h. Em 08/10, das ~22 rodadas previstas entre 12h40 e 23h50 UTC, rodaram 2. Nas 48 h de 07 e 08/10, os outros workflows mostram o mesmo padrão: quanto mais frequente o cron, mais ele é descartado.

   | Workflow | Previstos em 48 h | Executados |
   |---|---|---|
   | `auditoria-achados.yml` (de hora em hora) | 48 | 8 |
   | `pr-guardiao.yml` (de hora em hora) | 48 | 8 |
   | `auditoria-producao.yml` (2x/h em horário comercial) | 38 | 6 |
   | `deploy-check.yml` (a cada 6 h) | 8 | 6 |
   | `auditoria-llm.yml` (1x/dia) | 2 | 2 |

3. **Job `vigia`.** Para escapar do descarte, um job ficava ligado ~5h40 num laço que dormia 5 min entre checagens e, ao terminar, disparava o próximo por `workflow_dispatch` (que não é descartado). Funcionava, mas mantinha um runner ocupado 24 h por dia, mesmo sem nenhuma sessão no Jules: ~1.440 minutos de Actions por dia, quase todos dormindo.

## Decisão

1. O adaptador ganha a ação `rodada`: inicia a persona da hora se ainda não houver sessão dela nesta hora, aprova planos, responde perguntas paradas há 5 min e termina. Leva segundos.
2. O `jules.yml` não tem `schedule` nem job contínuo. Só aceita `workflow_dispatch`; o padrão da ação é `rodada`.
3. O relógio fica fora do GitHub. O cron-job.org chama a cada 30 min:

   ```
   POST https://api.github.com/repos/<dono>/<repo>/actions/workflows/jules.yml/dispatches
   Authorization: Bearer <token>
   Accept: application/vnd.github+json
   X-GitHub-Api-Version: 2022-11-28
   Content-Type: application/json
   User-Agent: devagent-cron

   {"ref":"main","inputs":{"acao":"rodada"}}
   ```

   O token é *fine-grained*, restrito a este repositório, só com **Actions: Read and write**. Resposta esperada: 204.
4. O laço `vigiar` continua no adaptador, sem uso, para um executor que não cobre por minuto parado.

## Consequências

- Custo: ~1 minuto faturado por rodada (o GitHub arredonda cada job para cima), cerca de 48 por dia.
- Regularidade: disparos por `workflow_dispatch` entram na fila e não são descartados.
- Disparos duplicados (um teste manual somado ao agendamento, por exemplo) não causam dano: o grupo de concorrência `jules` serializa as execuções e a segunda encontra a sessão criada pela primeira.
- Dependência nova fora do repositório: se o cron-job.org parar ou o token expirar, o agente para de ser acordado. O cron-job.org avisa por e-mail quando o job falha; a validade do token precisa de lembrete.
- Risco do token: quem o obtiver pode disparar workflows deste repositório (gastar minutos, iniciar sessões até o limite de `JULES_LIMITE_DIARIO`). Não lê nem altera código.
- Os demais workflows agendados ainda dependem do cron do GitHub e sofrem o mesmo descarte (tabela acima). O que mais pesa é a `auditoria-producao.yml`, o sensor que faz o agente perceber dados errados em produção. Se a correção ficar lenta por falta de auditoria, a mesma solução se aplica: trocar o `schedule` por um job no cron-job.org chamando `workflow_dispatch`.
