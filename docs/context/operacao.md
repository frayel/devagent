# Contexto · Operação

## Fluxo de entrega

```
Jules abre PR → CI (lint, tipos, testes, smoke) → automerge.yml faz squash merge
→ Render publica a main → deploy-check.yml confere o deploy
→ se falhou, abre issue `deploy-falhou` com logs → agente corrige no Passo 1
→ se live, auditoria-producao.yml confere o site contra fontes independentes
→ se o dado está errado, abre issue `producao-incorreta` → agente corrige no Passo 1
```

## Workflows

| Arquivo | Dispara | Faz |
|---|---|---|
| `ci.yml` | PR e push na `main` | ruff, mypy, pytest; job `smoke` sobe a app só com `requirements.txt` e testa `/healthz` e `/` |
| `automerge.yml` | CI concluído com sucesso em PR | squash merge e remoção da branch |
| `deploy-check.yml` | após o auto-merge, a cada 6 h, manual | consulta o Render; abre ou fecha issues `deploy-falhou`; dispara a auditoria quando o deploy fica live |
| `auditoria-producao.yml` | a cada 30 min no pregão, antes da abertura, após deploy | roda `auditoria/auditar.py` contra produção; abre ou fecha issues `producao-incorreta` |
| `auditoria-achados.yml` | de hora em hora e após merge de PR `auditoria:` | abre issues para os achados do auditor LLM em `docs/auditoria/achados/` |

O `automerge.yml` não faz merge de PRs que alteram o auditor (`auditoria/`, `docs/agents/auditor.md`, `automerge.yml`, `auditoria-*.yml`): aplica o label `revisao-humana` e espera um humano.

Merges feitos pelo `GITHUB_TOKEN` não disparam o `ci.yml` na `main`; por isso a verificação pós-merge fica no `deploy-check.yml`.

## Variáveis e secrets

| Nome | Onde | Uso |
|---|---|---|
| `RENDER_API_KEY` | secret do GitHub e ambiente do Jules | ler status e logs de deploy |
| `RENDER_SERVICE_ID` | secret do GitHub e ambiente do Jules | id `srv-...` do web service |
| `PRODUCTION_URL` | ambiente do Jules; variável (não secret) do GitHub, opcional | auditoria de produção; padrão `https://devagent-vb52.onrender.com` |
| `BRAPI_TOKEN` | Render | coletor brapi |

## Render: cuidados

- No plano gratuito, o serviço hiberna sem tráfego e o disco é efêmero: um SQLite local perde os dados a cada deploy ou reinício. Persistência exige disco persistente (plano pago) ou Postgres. Confira os planos atuais antes de decidir e registre a decisão em ADR.
- O health check usa `healthCheckPath: /healthz`; se a app não responder, o deploy fica `update_failed`.
- Diagnóstico: skill `docs/skills/diagnosticar-deploy.md` e `python scripts/render_status.py`.
