# Operação do núcleo

Como o trabalho do agente chega à produção e quem vigia cada etapa. Vale para qualquer projeto que use `devagent/`; particularidades do produto ficam em `docs/context/operacao.md`.

## Fluxo de entrega

```
Jules abre PR → CI (make verify, make smoke) → automerge.yml faz squash merge
→ a plataforma publica a main → deploy-check.yml confere o deploy
→ se falhou, abre issue `deploy-falhou` com logs → agente corrige no Passo 1
→ se live, auditoria-producao.yml confere o site contra fontes independentes (make audit)
→ se o dado está errado, abre issue `producao-incorreta` → agente corrige no Passo 1

PR com CI falhando ou em conflito → pr-guardiao.yml comenta @jules com o log
→ Jules corrige na mesma branch → CI passa → automerge
→ sem reação em 3 h, 4ª falha ou conflito grande → PR fechado + issue `tentativa-falhou`
→ spec continua `ready` na main → próximo ciclo refaz, lendo a issue
```

## Workflows

Todos ficam em `.github/workflows/` porque o GitHub exige. São do núcleo; o projeto só ajusta os horários marcados como tal.

| Arquivo | Dispara | Faz |
|---|---|---|
| `ci.yml` | PR e push na `main` | job `disciplina` com `python -m devagent.conferir_pr` (ADR 008); `make install` e `make verify`; job `smoke` com `make install-prod` e `make smoke` |
| `automerge.yml` | CI concluído com sucesso em PR | squash merge e remoção da branch; fecha as issues citadas com `Closes/Fixes/Resolves #N` no título, corpo ou commits do PR (exceto `deploy-falhou` e `producao-incorreta`) |
| `deploy-check.yml` | após o auto-merge, a cada 6 h, manual | consulta a plataforma (`devagent/adaptadores/render_status.py`); abre ou fecha issues `deploy-falhou`; dispara a auditoria quando o deploy fica live |
| `auditoria-producao.yml` | horários do projeto, após deploy | `make audit` contra produção; abre ou fecha issues `producao-incorreta` |
| `jules.yml` | `workflow_dispatch` com `acao=rodada` a cada 30 min, chamado de fora pelo cron-job.org (ADR 010); manual | `rodada` (`devagent/adaptadores/jules.py rodada`): inicia a persona da hora se ainda não começou nesta hora (Sentinel 03h, Bolt 09h, Palette 15h BRT, desenvolvedor nas demais; pula se uma sessão que altera código estiver ativa ou a cota de `JULES_LIMITE_DIARIO` chegar à reserva de 4), aprova planos pendentes, responde perguntas paradas há 5 min e encerra. Menos de 1 min por execução. Sem `schedule`: o cron do GitHub descarta a maior parte dos disparos frequentes |
| `auditoria-llm.yml` | horário do projeto, manual | cria a sessão do auditor LLM pela API do Jules |
| `pr-guardiao.yml` | CI falho em PR, após auto-merge, de hora em hora | `devagent/guardiao_prs.py`: cobra `@jules` (até 3x), fecha PR sem reação em 3 h, com conflito grande (> 3 arquivos ou > 40 linhas) ou substituído (`Substitui #N`); abre issue `tentativa-falhou`; fecha issues citadas com `Closes #N` em PRs mergeados nos últimos 7 dias; apaga branches órfãs com mais de 24 h |
| `auditoria-achados.yml` | de hora em hora e após merge de PR `auditoria:` | `devagent/auditoria/achados_para_issues.py`: abre issues para os achados do auditor LLM em `docs/auditoria/achados/` |

O `automerge.yml` não tem caminhos protegidos: todo PR com CI verde entra (ADR 007).

Merges feitos pelo `GITHUB_TOKEN` não fecham issues pelas palavras-chave `Closes #N` (o GitHub não processa); por isso o `automerge.yml` as fecha explicitamente, e precisa da permissão `issues: write`. Esses merges também não disparam o `ci.yml` na `main`; por isso a verificação pós-merge fica no `deploy-check.yml`.

## Relógio externo (cron-job.org)

O agente só trabalha quando é acordado, e o `schedule` do GitHub Actions não serve para isso: ele descarta a maior parte dos disparos frequentes (em 48 h, só 8 de 48 disparos de hora em hora rodaram). Um job contínuo que esperasse dentro do Actions resolvia o atraso, mas cobrava minutos parado, 24 h por dia. Por isso o relógio fica fora do GitHub (ADR 010).

Configuração, uma vez por repositório:

1. **Token no GitHub:** Settings → Developer settings → Fine-grained tokens. Acesso só a este repositório, permissão **Actions: Read and write** e nenhuma outra. Anote a validade e crie um lembrete para renovar.
2. **Job no cron-job.org:**

   | Campo | Valor |
   |---|---|
   | URL | `https://api.github.com/repos/<dono>/<repo>/actions/workflows/jules.yml/dispatches` |
   | Agenda | a cada 30 min |
   | Método | `POST` |
   | Cabeçalhos | `Authorization: Bearer <token>`, `Accept: application/vnd.github+json`, `X-GitHub-Api-Version: 2022-11-28`, `Content-Type: application/json`, `User-Agent: devagent-cron` |
   | Corpo | `{"ref":"main","inputs":{"acao":"rodada"}}` |

3. **Conferir:** a resposta esperada é 204, e uma execução "Jules" aparece na aba Actions. 401 é token inválido ou expirado; 403, falta a permissão de Actions; 422, corpo ou input errado. Ative o aviso por e-mail de falha do cron-job.org: é assim que um token expirado aparece.

Disparos duplicados não causam dano: as execuções do `jules.yml` são serializadas e a segunda encontra a sessão criada pela primeira.

## Secrets e variáveis do núcleo

| Nome | Onde | Uso |
|---|---|---|
| `RENDER_API_KEY` | secret do GitHub e ambiente do Jules | ler status e logs de deploy |
| `RENDER_SERVICE_ID` | secret do GitHub e ambiente do Jules | id `srv-...` do web service |
| `RENDER_DEPLOY_HOOK_URL` | ambiente do Jules, opcional | disparo manual de deploy (Passo 3) |
| `JULES_API_KEY` | secret do GitHub | criar e destravar sessões do Jules |
| `JULES_LIMITE_DIARIO` | variável (não secret) do GitHub, opcional | tarefas do plano do Jules por 24 h (15, 100 ou 300); o desenvolvedor para ao chegar a 4 do limite, reservando a cota dos especialistas e do auditor |
| token do relógio | cron-job.org (não fica no GitHub) | token fine-grained com Actions: Read and write, usado para chamar `workflow_dispatch` do `jules.yml` |
| `JULES_SOURCE` | ambiente, opcional | sobrescreve a fonte derivada de `repositorio` no `devagent.toml` |
| `PRODUCTION_URL` | ambiente do Jules; variável (não secret) do GitHub, opcional | sobrescreve `producao_url` do `devagent.toml` |
| `DEVAGENT_CONFIG` | ambiente, opcional | caminho de outro `devagent.toml` |

## Render: cuidados do adaptador

- No plano gratuito, o serviço hiberna sem tráfego e o disco é efêmero: um SQLite local perde os dados a cada deploy ou reinício. Persistência exige disco persistente (plano pago) ou Postgres. Confira os planos atuais antes de decidir e registre a decisão em ADR.
- O health check usa `healthCheckPath` do `render.yaml`; se a app não responder, o deploy fica `update_failed`. O `make smoke` lê o mesmo caminho.
- Diagnóstico: skill `devagent/skills/diagnosticar-deploy.md` e `python -m devagent.adaptadores.render_status`.

## Trocar um adaptador

- **Outra plataforma de deploy:** escreva `devagent/adaptadores/<plataforma>_status.py` com a mesma saída (JSON e códigos 0, 1, 3), aponte o `deploy-check.yml` para ele e mude `[deploy] adaptador` no `devagent.toml`.
- **Outro executor de agente:** substitua `devagent/adaptadores/jules.py`, os workflows `jules.yml` e `auditoria-llm.yml` e o alvo do relógio externo. Os prompts só apontam para `AGENTS.md`, `devagent/CICLO.md` e `devagent/agents/`, então a instrução continua a mesma.
