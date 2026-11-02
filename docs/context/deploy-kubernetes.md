# Contexto · Deploy em Kubernetes

Decisão em `docs/decisions/010-deploy-kubernetes.md`. Arquivos: `Dockerfile`, `.dockerignore`, `k8s/web/` (Deployment, Service, Ingress), `k8s/deploy.sh` e `.github/workflows/deploy-k8s.yml`.

## Fluxo

1. Merge na `main` (pelo `automerge.yml` ou humano) ou disparo manual.
2. Job `build` (ubuntu-latest): `docker build`, push de `ghcr.io/frayel/devagent/web:<sha>` e `:latest` com o `GITHUB_TOKEN`; apaga imagens com mais de uma semana, guardando as 5 últimas.
3. Job `deploy` (runner `self-hosted, painelb3` no servidor): escreve `.env.docker` a partir de `PAINELB3_ENV`, cria o namespace e o `ghcr-secret`, troca o host no Ingress e a tag no Deployment, roda `k8s/deploy.sh` (Secret `secret-store`, apply, `rollout status`) e confere `https://<K8S_HOST>/healthz`.

## GitHub: Settings → Secrets and variables → Actions

| Nome | Aba | Obrigatório | Conteúdo |
|---|---|---|---|
| `K8S_HOST` | Variables | sim (liga o workflow) | domínio público, sem `https://`, ex. `painel.exemplo.com` |
| `KUBECTL` | Variables | não | comando do kubectl no runner; padrão `microk8s kubectl` |
| `PAINELB3_ENV` | Secrets | sim | arquivo `.env` com as variáveis do app (abaixo), uma `CHAVE=valor` por linha, sem aspas |
| `GHCR_USUARIO` | Secrets | sim | usuário do GitHub dono do token abaixo |
| `GHCR_TOKEN` | Secrets | sim | PAT classic só com `read:packages`, para o cluster baixar a imagem privada (o `GITHUB_TOKEN` expira com o job e o pod precisa baixar de novo ao reiniciar) |

O `GITHUB_TOKEN` cobre o push da imagem; não precisa de secret para isso.

## Conteúdo de `PAINELB3_ENV`

As mesmas variáveis da seção 10 do `PRODUTO.md`, que hoje estão no painel do Render. `GIT_COMMIT` é acrescentada pelo workflow.

```
DATABASE_URL=postgresql://usuario:senha@host:5432/banco
CONSULTOR_SENHA=...
BRAPI_TOKEN=...
MT5_API_URL=http://host:8000/api/v1
MT5_API_KEY=...
GEMINI_API_KEY=...
GITHUB_TOKEN=...
JULES_API_KEY=...
COLETA_AUTOMATICA=0
```

Obrigatória: `DATABASE_URL` (sem ela o app cai no SQLite dentro do pod e perde os dados a cada deploy). As demais são opcionais, com o comportamento descrito no `PRODUTO.md`. `RENDER_API_KEY` não tem uso aqui.

**Coleta em dobro.** Enquanto o Render estiver ligado com o mesmo banco, só um dos dois coleta. Comece com `COLETA_AUTOMATICA=0` no Kubernetes; na virada, inverta (tire a linha daqui e ponha `COLETA_AUTOMATICA=0` no Render, ou desligue o Render).

## No servidor (uma vez)

1. Registrar um runner self-hosted em `frayel/devagent` (Settings → Actions → Runners → New self-hosted runner) com as labels `self-hosted,painelb3`. O runner do dux pertence a outra conta e não serve. O usuário do runner precisa rodar `microk8s kubectl` (grupo `microk8s`).
2. Conferir que o ClusterIssuer `letsencrypt` existe (`microk8s kubectl get clusterissuer`). O deploy não o cria, para não mexer no do dux.
3. Apontar o DNS do `K8S_HOST` para o IP do ingress.
4. Liberar o IP do servidor no firewall do Postgres e da mt5api, se houver.

## Rollback

```
microk8s kubectl -n painelb3 rollout undo deployment/web
```
