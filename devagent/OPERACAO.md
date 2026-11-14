# Operação do núcleo

Como o trabalho do agente chega à produção e quem vigia cada etapa. Vale para qualquer projeto que use `devagent/`; particularidades do produto ficam em `docs/context/operacao.md`.

## Fluxo de entrega

```
Agente (Antigravity) abre PR → CI (make verify, make smoke, disciplina) → automerge.yml faz squash merge
→ a plataforma publica a main → deploy-check.yml confere o deploy
→ se falhou, abre issue `deploy-falhou` com logs → agente corrige no Passo 1
→ se live, auditoria-producao.yml confere o site contra fontes independentes (make audit)
→ se o dado está errado, abre issue `producao-incorreta` → agente corrige no Passo 1

Em paralelo, na mesma rodada (ADR 021):
fila com até 2 specs ready → Especificador abre PR `spec:` (só docs/specs, backlog, estado, runs)
spec ready sem `revisada:` → Revisor abre PR `revisão:` → a spec entra na fila do desenvolvimento
merges do desenvolvimento → Verificador abre PR `verificação:` → achados viram issues `verificacao`

PR com CI falhando ou em conflito → pr-guardiao.yml comenta @antigravity com o log
→ agente corrige na mesma branch → CI passa → automerge
→ sem reação em 3 h, 4ª falha ou conflito grande → PR fechado + issue `tentativa-falhou`
→ spec continua `ready` na main → próximo ciclo refaz, lendo a issue
```

## Workflows

Todos ficam em `.github/workflows/` porque o GitHub exige. São do núcleo; o projeto só ajusta os horários marcados como tal.

| Arquivo | Dispara | Faz |
|---|---|---|
| `ci.yml` | PR e push na `main` | job `disciplina` com `python -m devagent.conferir_pr` (ADR 008, 024 e 032); `make install` e `make verify`; job `smoke` com `make install-prod` e `make smoke` |
| `automerge.yml` | CI concluído com sucesso em PR | squash merge e remoção da branch; fecha as issues citadas com `Closes/Fixes/Resolves #N` no título, corpo ou commits do PR (exceto `deploy-falhou` e `producao-incorreta`) |
| `deploy-check.yml` | após o auto-merge, a cada 6 h, manual | consulta a plataforma (`devagent/adaptadores/render_status.py`); abre ou fecha issues `deploy-falhou`; dispara a auditoria quando o deploy fica live |
| `auditoria-producao.yml` | horários do projeto, após deploy | `make audit` contra produção; abre ou fecha issues `producao-incorreta`. Job `saude`: lê a página de saúde do produto (`python -m devagent.saude`, ADR 016) e abre, atualiza ou fecha a issue `sistema-com-problema` |
| `pr-guardiao.yml` | CI falho em PR, após auto-merge, de hora em hora | `devagent/guardiao_prs.py`: cobra `@antigravity` (até 3x), fecha PR sem reação em 3 h (o de raia paralela fecha sem `tentativa-falhou`; a raia recomeça na rodada seguinte), com conflito grande (> 3 arquivos ou > 40 linhas, sem contar trechos só de acréscimo, ADR 017) ou substituído (`Substitui #N`); abre issue `tentativa-falhou` com a spec do PR, salvo se o conteúdo do PR já está na `main` (ADR 014) ou se é especialista sem achado (ADRs 019 e 020); fecha na hora PR de verificação sem achado novo em `docs/verificacao/achados/`, sem issue (ADR 025); fecha `tentativa-falhou` órfã, cuja spec já está `done` na `main` ou que não cita spec (ADR 020); fecha issues citadas com `Closes #N` em PRs mergeados nos últimos 7 dias; aplica `prioridade` a issue `bug` aberta há mais de 24 h (ADR 030); apaga branches órfãs com mais de 24 h |
| `auditoria-achados.yml` | de hora em hora e após merge de PR `auditoria:` ou `verificação:` | `devagent/auditoria/achados_para_issues.py`: abre issues para os achados do auditor LLM em `docs/auditoria/achados/` e do Verificador em `docs/verificacao/achados/` (label `verificacao`; `alta` e `media` com `prioridade`) |
| `jules.yml` e `auditoria-llm.yml` | só manual (`workflow_dispatch`) | legado do executor anterior (`devagent/adaptadores/jules.py`): iniciam sessões pela API do Jules. Sem agendamento desde o ADR 032; precisam de `JULES_API_KEY` |

O `automerge.yml` não tem caminhos protegidos: todo PR com CI verde entra (ADR 007).

Merges feitos pelo `GITHUB_TOKEN` não fecham issues pelas palavras-chave `Closes #N` (o GitHub não processa); por isso o `automerge.yml` as fecha explicitamente, e precisa da permissão `issues: write`. Esses merges também não disparam o `ci.yml` na `main`; por isso a verificação pós-merge fica no `deploy-check.yml`.

## Agendamento e Execução (Modelo Híbrido · ADR 032)

O sistema opera no modelo híbrido, eliminando a dependência do cron de 5 minutos e da API do Jules:

1. **Automação agendada no Antigravity Remote (a cada 2h):**
   - Garante o batimento contínuo do projeto: a sessão do desenvolvedor (skill `/ciclo`) percorre o ciclo de decisão do `CICLO.md` (produção, PR aberto, specs revisadas, documentação e issues).
   - Especialistas (Sentinel de madrugada, Bolt pela manhã), auditor e raias paralelas rodam em tarefas agendadas próprias, cujo prompt nomeia a persona. A sessão do desenvolvedor nunca assume uma persona pelo horário nem pela fila (`devagent/agents/especialistas.md`, regra 7, e ADR 024).
   - Configurada diretamente na interface do Antigravity Remote apontando para o workspace.
2. **Modo Contínuo Sob Demanda (`/goal`):**
   - Quando o desenvolvedor precisa acelerar entregas ou fechar um lote de trabalho, aciona o comando `/goal` com a meta (ex: implementar as 3 próximas specs ou corrigir issues prioritárias). O agente encadeia múltiplos passos e commits até concluir o objetivo.
3. **Disparos Manuais (`workflow_dispatch`):**
   - Disponíveis para acionar checagens de deploy ou auditorias pontuais via GitHub Actions.

## Secrets e variáveis do núcleo

| Nome | Onde | Uso |
|---|---|---|
| `RENDER_API_KEY` | secret do GitHub e ambiente do agente | ler status e logs de deploy |
| `RENDER_SERVICE_ID` | secret do GitHub e ambiente do agente | id `srv-...` do web service |
| `RENDER_DEPLOY_HOOK_URL` | ambiente do agente, opcional | disparo manual de deploy (Passo 3) |
| `PRODUCTION_URL` | ambiente do agente; variável (não secret) do GitHub, opcional | sobrescreve `producao_url` do `devagent.toml` |
| `DEVAGENT_CONFIG` | ambiente, opcional | caminho de outro `devagent.toml` |
| `SAUDE_SENHA` | secret do GitHub e ambiente do agente, se a página de saúde pede senha | senha do HTTP Basic da página de saúde; o usuário fica em `[saude] usuario` no `devagent.toml` |

## Render: cuidados do adaptador

- No plano gratuito, o serviço hiberna sem tráfego e o disco é efêmero: um SQLite local perde os dados a cada deploy ou reinício. Persistência exige disco persistente (plano pago) ou Postgres. Confira os planos atuais antes de decidir e registre a decisão em ADR.
- O health check usa `healthCheckPath` do `render.yaml`; se a app não responder, o deploy fica `update_failed`. O `make smoke` lê o mesmo caminho. O `devagent/smoke.sh` reprova se a porta já responde antes de a aplicação subir e, ao sair, encerra o servidor e todos os processos filhos.
- Diagnóstico: skill `devagent/skills/diagnosticar-deploy.md` e `python -m devagent.adaptadores.render_status`.

## Trocar um adaptador

- **Outra plataforma de deploy:** escreva `devagent/adaptadores/<plataforma>_status.py` com a mesma saída (JSON e códigos 0, 1, 3), aponte o `deploy-check.yml` para ele e mude `[deploy] adaptador` no `devagent.toml`.
- **Outro executor de agente:** as instruções estão em `AGENTS.md`, `devagent/CICLO.md` e `devagent/agents/`, desacopladas de APIs proprietárias (ADR 032).
