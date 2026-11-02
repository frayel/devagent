# ADR 010 · Deploy em Kubernetes próprio, ao lado do Render

- **Data:** 2026-11-02 · **Status:** aceita
- **Complementa:** a linha *Deploy* da seção 2 do `PRODUTO.md`

## Contexto

O dono do produto tem um servidor Kubernetes (microk8s) que já hospeda o dux, com ingress nginx, cert-manager e o ClusterIssuer `letsencrypt`. A intenção é que ele seja o endereço definitivo do painel. O Render continua no ar durante a transição.

## Decisão

1. A imagem do app sai do `Dockerfile` da raiz e vai para `ghcr.io/frayel/devagent/web`, com a tag do commit.
2. O `.github/workflows/deploy-k8s.yml` constrói a imagem num runner do GitHub e aplica `k8s/` num runner self-hosted no servidor (labels `self-hosted, painelb3`), no namespace `painelb3`, pelo `k8s/deploy.sh`. É o padrão do `staging.yml` do dux.
3. Uma réplica, sem HPA: a coleta roda dentro do processo (ADR 004) e duas réplicas coletariam em dobro.
4. As variáveis do app chegam por um único secret do GitHub, `PAINELB3_ENV`, no formato de arquivo `.env`, que vira o Secret `secret-store` do namespace.
5. O workflow só roda com a variável de repositório `K8S_HOST` definida. Sem ela, nada muda na esteira.

## Consequências

- Enquanto os dois deploys estiverem ligados com o mesmo `DATABASE_URL`, os dois agendadores coletam. Um deles deve ter `COLETA_AUTOMATICA=0`.
- `deploy-check.yml`, a auditoria e o `producao_url` do `devagent.toml` continuam olhando o Render. Trocar a produção para o Kubernetes é outro passo: mudar `producao_url` (ou `PRODUCTION_URL`) e escrever um adaptador `devagent/adaptadores/<plataforma>_status.py`, como prevê `devagent/OPERACAO.md`.
- O commit em produção aparece em `/sistema` pela variável `GIT_COMMIT`, gravada na imagem e no Secret.
