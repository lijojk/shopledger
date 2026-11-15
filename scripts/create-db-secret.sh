#!/usr/bin/env bash
# Creates the database secret once per namespace. The password never enters Git.
# Usage: create-db-secret.sh <staging|production>
set -euo pipefail

NAMESPACE="${1:?usage: create-db-secret.sh <staging|production>}"

kubectl create namespace "${NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -

if kubectl -n "${NAMESPACE}" get secret shopledger-db >/dev/null 2>&1; then
  echo "secret shopledger-db already exists in ${NAMESPACE}, leaving it unchanged"
  exit 0
fi

password=$(openssl rand -hex 24)
kubectl -n "${NAMESPACE}" create secret generic shopledger-db \
  --from-literal=POSTGRES_PASSWORD="${password}" \
  --from-literal=DATABASE_URL="postgresql+psycopg://shopledger:${password}@postgres:5432/shopledger"
echo "secret shopledger-db created in ${NAMESPACE}"
