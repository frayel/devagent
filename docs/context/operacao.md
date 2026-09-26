# Contexto · Operação

## Fluxo de entrega

```
Jules abre PR → CI (lint, tipos, testes, smoke) → automerge.yml faz squash merge
→ Render publica a main → deploy-check.yml confere o deploy
→ se falhou, abre issue `deploy-falhou` com logs → agente corrige no Passo 1
```

## Workflows

| Arquivo | Dispara | Faz |
|---|---|---|
| `ci.yml` | PR e push na `main` | ruff, mypy, pytest; job `smoke` sobe a app só com `requirements.txt` e testa `/healthz` e `/` |
| `automerge.yml` | CI concluído com sucesso em PR | squash merge e remoção da branch |
| `deploy-check.yml` | após o auto-merge, a cada 6 h, manual | consulta o Render; abre ou fecha issues `deploy-falhou` |

Merges feitos pelo `GITHUB_TOKEN` não disparam o `ci.yml` na `main`; por isso a verificação pós-merge fica no `deploy-check.yml`.

## Variáveis e secrets

| Nome | Onde | Uso |
|---|---|---|
| `RENDER_API_KEY` | secret do GitHub e ambiente do Jules | ler status e logs de deploy |
| `RENDER_SERVICE_ID` | secret do GitHub e ambiente do Jules | id `srv-...` do web service |
| `PRODUCTION_URL` | ambiente do Jules | checar `/healthz` em produção |
| `BRAPI_TOKEN` | Render | coletor brapi |

## Render: cuidados

- No plano gratuito, o serviço hiberna sem tráfego e o disco é efêmero: um SQLite local perde os dados a cada deploy ou reinício. Persistência exige disco persistente (plano pago) ou Postgres. Confira os planos atuais antes de decidir e registre a decisão em ADR.
- O health check usa `healthCheckPath: /healthz`; se a app não responder, o deploy fica `update_failed`.
- Diagnóstico: skill `docs/skills/diagnosticar-deploy.md` e `python scripts/render_status.py`.
