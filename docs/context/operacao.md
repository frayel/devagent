# Contexto · Operação

## Fluxo de entrega

```
Jules abre PR → CI (lint, tipos, testes, smoke) → automerge.yml faz squash merge
→ Render publica a main → deploy-check.yml confere o deploy
→ se falhou, abre issue `deploy-falhou` com logs → agente corrige no Passo 1
→ se live, auditoria-producao.yml confere o site contra fontes independentes
→ se o dado está errado, abre issue `producao-incorreta` → agente corrige no Passo 1

PR com CI falhando ou em conflito → pr-guardiao.yml comenta @jules com o log
→ Jules corrige na mesma branch → CI passa → automerge
→ sem reação em 3 h, 4ª falha ou conflito grande → PR fechado + issue `tentativa-falhou`
→ spec continua `ready` na main → próximo ciclo refaz, lendo a issue
```

## Workflows

| Arquivo | Dispara | Faz |
|---|---|---|
| `ci.yml` | PR e push na `main` | ruff, mypy, pytest; job `smoke` sobe a app só com `requirements.txt` e testa `/healthz` e `/` |
| `automerge.yml` | CI concluído com sucesso em PR | squash merge e remoção da branch; fecha as issues citadas com `Closes/Fixes/Resolves #N` no título, corpo ou commits do PR (exceto `deploy-falhou` e `producao-incorreta`) |
| `deploy-check.yml` | após o auto-merge, a cada 6 h, manual | consulta o Render; abre ou fecha issues `deploy-falhou`; dispara a auditoria quando o deploy fica live |
| `auditoria-producao.yml` | a cada 30 min no pregão, antes da abertura, após deploy | roda `auditoria/auditar.py` contra produção; abre ou fecha issues `producao-incorreta` |
| `jules.yml` | de hora em hora aos :47 (24 h por dia), destravar aos :04, :19, :34 e :49, manual | cria sessões pela API do Jules (`scripts/jules.py`), sem exigir aprovação de plano: desenvolvedor 21x por dia (pula se a sessão anterior ainda estiver ativa ou se a cota de `JULES_LIMITE_DIARIO` chegar à reserva de 4); Sentinel 03h47, Bolt 09h47 e Palette 15h47 (BRT), uma vez cada; só uma persona que altera código trabalha por vez; a cada 15 min aprova planos pendentes e responde perguntas paradas |
| `auditoria-llm.yml` | dias úteis 18h41 BRT, manual | cria a sessão do auditor LLM pela API do Jules |
| `pr-guardiao.yml` | CI falho em PR, após auto-merge, de hora em hora | roda `scripts/guardiao_prs.py`: cobra `@jules` (até 3x), fecha PR sem reação em 3 h, com conflito grande (> 3 arquivos ou > 40 linhas) ou substituído (`Substitui #N`); abre issue `tentativa-falhou`; fecha issues citadas com `Closes #N` em PRs mergeados nos últimos 7 dias; apaga branches órfãs com mais de 24 h |
| `auditoria-achados.yml` | de hora em hora e após merge de PR `auditoria:` | abre issues para os achados do auditor LLM em `docs/auditoria/achados/` |

O `automerge.yml` não faz merge de PRs que alteram o auditor ou o guardião (`auditoria/`, `docs/agents/auditor.md`, `automerge.yml`, `auditoria-*.yml`, `pr-guardiao.yml`, `scripts/guardiao_prs.py`, `jules.yml`, `scripts/jules.py`): aplica o label `revisao-humana` e espera um humano.

Merges feitos pelo `GITHUB_TOKEN` não fecham issues pelas palavras-chave `Closes #N` (o GitHub não processa); por isso o `automerge.yml` as fecha explicitamente, e precisa da permissão `issues: write`. Esses merges também não disparam o `ci.yml` na `main`; por isso a verificação pós-merge fica no `deploy-check.yml`.

## Variáveis e secrets

| Nome | Onde | Uso |
|---|---|---|
| `RENDER_API_KEY` | secret do GitHub e ambiente do Jules | ler status e logs de deploy |
| `RENDER_SERVICE_ID` | secret do GitHub e ambiente do Jules | id `srv-...` do web service |
| `JULES_API_KEY` | secret do GitHub | criar e destravar sessões do Jules (`scripts/jules.py`) |
| `JULES_LIMITE_DIARIO` | variável (não secret) do GitHub, opcional | tarefas do plano do Jules por 24 h (15, 100 ou 300); o desenvolvedor para ao chegar a 4 do limite, reservando a cota dos especialistas e do auditor |
| `PRODUCTION_URL` | ambiente do Jules; variável (não secret) do GitHub, opcional | auditoria de produção; padrão `https://devagent-vb52.onrender.com` |
| `BRAPI_TOKEN` | Render | coletor brapi (sem ele, a coleta usa só o Yahoo Finance) |
| `COLETA_AUTOMATICA` | Render, opcional | `0` desliga a coleta dentro do web service |
| `DATABASE_PATH` | Variável de ambiente (opcional) | caminho do banco SQLite (padrão `data.db`) |

## Render: cuidados

- No plano gratuito, o serviço hiberna sem tráfego e o disco é efêmero: um SQLite local perde os dados a cada deploy ou reinício. Persistência exige disco persistente (plano pago) ou Postgres. Confira os planos atuais antes de decidir e registre a decisão em ADR.
- O health check usa `healthCheckPath: /healthz`; se a app não responder, o deploy fica `update_failed`.
- Diagnóstico: skill `docs/skills/diagnosticar-deploy.md` e `python scripts/render_status.py`.
