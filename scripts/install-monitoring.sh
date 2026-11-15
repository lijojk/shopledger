#!/usr/bin/env bash
# Installs or upgrades Prometheus, Grafana and Alertmanager, then adds our own
# ServiceMonitor, alert rules and dashboard.
# Usage: install-monitoring.sh [extra helm arguments]
set -euo pipefail

NAMESPACE=monitoring
kubectl create namespace "${NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -

if ! kubectl -n "${NAMESPACE}" get secret grafana-admin >/dev/null 2>&1; then
  password=$(openssl rand -hex 12)
  kubectl -n "${NAMESPACE}" create secret generic grafana-admin \
    --from-literal=admin-user=admin \
    --from-literal=admin-password="${password}"
  echo "Grafana password: ${password}  (shown once, you can read it back from the secret)"
fi

helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update prometheus-community
helm upgrade --install monitoring prometheus-community/kube-prometheus-stack \
  --namespace "${NAMESPACE}" \
  --values monitoring/values.yaml \
  --wait --timeout 15m "$@"

kubectl apply -f monitoring/servicemonitor.yaml
kubectl apply -f monitoring/alerts.yaml
kubectl -n "${NAMESPACE}" create configmap shopledger-dashboard \
  --from-file=monitoring/dashboards/shopledger.json \
  --dry-run=client -o yaml |
  kubectl label --local -f - grafana_dashboard=1 -o yaml |
  kubectl apply -f -
echo "monitoring is installed"
