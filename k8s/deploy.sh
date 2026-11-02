#!/bin/sh
# Aplica o Painel B3 no namespace painelb3. Chamado pelo deploy-k8s.yml no
# runner self-hosted do servidor, depois de trocar os marcadores dos YAMLs.
# KUBECTL permite usar kubectl puro fora do microk8s.
set -eu

KUBECTL="${KUBECTL:-microk8s kubectl}"
NS=painelb3

echo "-----------------------------------------------------------------------------------------"
echo "                                 KUBERNETES DEPLOYING..."
echo "-----------------------------------------------------------------------------------------"

echo "Namespace..."
$KUBECTL create namespace "$NS" --dry-run=client -o yaml | $KUBECTL apply -f -

echo "Secret Store..."
# Recriado a cada deploy a partir do secret PAINELB3_ENV do GitHub.
$KUBECTL create secret generic secret-store --from-env-file=.env.docker \
  --namespace="$NS" --dry-run=client -o yaml | $KUBECTL apply -f -

echo "Web..."
$KUBECTL apply -f k8s/web/deploy.yaml,k8s/web/service.yaml,k8s/web/ingress.yaml
$KUBECTL rollout status deployment/web --namespace="$NS" --timeout=300s

echo "-----------------------------------------------------------------------------------------"
echo "                                         DEPLOY FINISHED."
echo "-----------------------------------------------------------------------------------------"
$KUBECTL get all,ingress --namespace="$NS"
