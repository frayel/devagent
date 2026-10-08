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
| `jules.yml` | só manual (`workflow_dispatch`); o job `vigia` contínuo foi removido para não consumir minutos do Actions | inicia uma persona (`desenvolvedor`, `seguranca`, `design`, `performance`, `auditor`) ou executa `destravar`, `listar`, `encerrar` pela API do Jules (`devagent/adaptadores/jules.py`). Sem o vigia, nada aprova planos pendentes nem responde perguntas sozinho: rode `destravar` quando precisar |
| `auditoria-llm.yml` | horário do projeto, manual | cria a sessão do auditor LLM pela API do Jules |
| `pr-guardiao.yml` | CI falho em PR, após auto-merge, de hora em hora | `devagent/guardiao_prs.py`: cobra `@jules` (até 3x), fecha PR sem reação em 3 h, com conflito grande (> 3 arquivos ou > 40 linhas) ou substituído (`Substitui #N`); abre issue `tentativa-falhou`; fecha issues citadas com `Closes #N` em PRs mergeados nos últimos 7 dias; apaga branches órfãs com mais de 24 h |
| `auditoria-achados.yml` | de hora em hora e após merge de PR `auditoria:` | `devagent/auditoria/achados_para_issues.py`: abre issues para os achados do auditor LLM em `docs/auditoria/achados/` |

O `automerge.yml` não tem caminhos protegidos: todo PR com CI verde entra (ADR 007).

Merges feitos pelo `GITHUB_TOKEN` não fecham issues pelas palavras-chave `Closes #N` (o GitHub não processa); por isso o `automerge.yml` as fecha explicitamente, e precisa da permissão `issues: write`. Esses merges também não disparam o `ci.yml` na `main`; por isso a verificação pós-merge fica no `deploy-check.yml`.

## Secrets e variáveis do núcleo

| Nome | Onde | Uso |
|---|---|---|
| `RENDER_API_KEY` | secret do GitHub e ambiente do Jules | ler status e logs de deploy |
| `RENDER_SERVICE_ID` | secret do GitHub e ambiente do Jules | id `srv-...` do web service |
| `RENDER_DEPLOY_HOOK_URL` | ambiente do Jules, opcional | disparo manual de deploy (Passo 3) |
| `JULES_API_KEY` | secret do GitHub | criar e destravar sessões do Jules |
| `JULES_LIMITE_DIARIO` | variável (não secret) do GitHub, opcional | tarefas do plano do Jules por 24 h (15, 100 ou 300); o desenvolvedor para ao chegar a 4 do limite, reservando a cota dos especialistas e do auditor |
| `JULES_SOURCE` | ambiente, opcional | sobrescreve a fonte derivada de `repositorio` no `devagent.toml` |
| `PRODUCTION_URL` | ambiente do Jules; variável (não secret) do GitHub, opcional | sobrescreve `producao_url` do `devagent.toml` |
| `DEVAGENT_CONFIG` | ambiente, opcional | caminho de outro `devagent.toml` |

## Render: cuidados do adaptador

- No plano gratuito, o serviço hiberna sem tráfego e o disco é efêmero: um SQLite local perde os dados a cada deploy ou reinício. Persistência exige disco persistente (plano pago) ou Postgres. Confira os planos atuais antes de decidir e registre a decisão em ADR.
- O health check usa `healthCheckPath` do `render.yaml`; se a app não responder, o deploy fica `update_failed`. O `make smoke` lê o mesmo caminho.
- Diagnóstico: skill `devagent/skills/diagnosticar-deploy.md` e `python -m devagent.adaptadores.render_status`.

## Trocar um adaptador

- **Outra plataforma de deploy:** escreva `devagent/adaptadores/<plataforma>_status.py` com a mesma saída (JSON e códigos 0, 1, 3), aponte o `deploy-check.yml` para ele e mude `[deploy] adaptador` no `devagent.toml`.
- **Outro executor de agente:** substitua `devagent/adaptadores/jules.py` e os workflows `jules.yml` e `auditoria-llm.yml`. Os prompts só apontam para `AGENTS.md`, `devagent/CICLO.md` e `devagent/agents/`, então a instrução continua a mesma.
